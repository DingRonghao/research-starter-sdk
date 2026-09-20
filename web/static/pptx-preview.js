export function correctPptxThemeBackgrounds(viewer, container) {
  const presentation = viewer.presentationData;
  if (!presentation) return;
  for (const [position, slide] of presentation.slides.entries()) {
    const layoutKey = slide.layoutIndex;
    const layout = presentation.layouts.get(layoutKey);
    const masterKey = presentation.layoutToMaster.get(layoutKey);
    const master = presentation.masters.get(masterKey);
    const themeKey = presentation.masterToTheme.get(masterKey);
    const background = slide.background || layout?.background || master?.background;
    const bgRef = background?.child('bgRef');
    const index = bgRef?.numAttr('idx');
    const scheme = bgRef?.child('schemeClr').attr('val');
    if (!bgRef?.exists() || index !== 1001 || !master || !scheme) continue;
    const mapped = layout?.colorMapOverride?.get(scheme) || master.colorMap.get(scheme) || scheme;
    const themes = [...presentation.themes.values()];
    const exactTheme = presentation.themes.get(themeKey);
    const candidateColors = [...new Set(themes.map(item => item.colorScheme.get(mapped)).filter(Boolean))];
    const theme = exactTheme || (
      candidateColors.length === 1 && candidateColors[0].replace(/^#/, '').toUpperCase() === 'FFFFFF'
        ? themes.find(item => item.colorScheme.get(mapped) === candidateColors[0])
        : null
    );
    const color = theme?.colorScheme.get(mapped);
    const fill = theme?.bgFillStyles?.[0];
    const placeholder = fill?.child('schemeClr');
    if (!color || fill?.localName !== 'solidFill' || placeholder?.attr('val')?.toLowerCase() !== 'phclr' || placeholder.allChildren().length) continue;
    const rendered = container.querySelector(`[data-slide-index="${position}"]`)?.firstElementChild?.firstElementChild;
    if (rendered) rendered.style.backgroundColor = `#${color.replace(/^#/, '')}`;
  }
}

export async function openPptxPreview(container, buffer) {
  const {PptxViewer, RECOMMENDED_ZIP_LIMITS} = await import('/vendor/pptx-renderer/aiden0z-pptx-renderer.browser.es.js');
  const viewer = await PptxViewer.open(buffer, container, {
    renderMode: 'list',
    scrollContainer: container,
    zipLimits: RECOMMENDED_ZIP_LIMITS,
    listOptions: {windowed: false, batchSize: 8},
    lazySlides: false,
    lazyMedia: false,
  });
  viewer.addEventListener('rendercomplete', () => correctPptxThemeBackgrounds(viewer, container));
  correctPptxThemeBackgrounds(viewer, container);
  return viewer;
}
