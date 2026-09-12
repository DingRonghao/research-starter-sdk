import * as pdfjsLib from '/vendor/pdfjs/pdf.min.mjs';
pdfjsLib.GlobalWorkerOptions.workerSrc='/vendor/pdfjs/pdf.worker.min.mjs';

export async function renderPdf(container,url){
  try{
    const pdf=await pdfjsLib.getDocument({url}).promise;
    container.innerHTML='';
    for(let number=1;number<=pdf.numPages;number+=1){
      const page=await pdf.getPage(number);
      const base=page.getViewport({scale:1});
      const cssScale=Math.min(2,Math.max(1,(container.clientWidth-28)/base.width));
      const viewport=page.getViewport({scale:cssScale});
      const outputScale=Math.min(3,Math.max(2,window.devicePixelRatio||1));
      const canvas=document.createElement('canvas');
      canvas.width=Math.floor(viewport.width*outputScale);
      canvas.height=Math.floor(viewport.height*outputScale);
      canvas.style.width=`${Math.floor(viewport.width)}px`;
      canvas.style.height=`${Math.floor(viewport.height)}px`;
      canvas.setAttribute('aria-label',`PDF 第 ${number} 页`);
      container.appendChild(canvas);
      await page.render({canvasContext:canvas.getContext('2d'),viewport,transform:[outputScale,0,0,outputScale,0,0]}).promise;
    }
  }catch(error){
    container.innerHTML=`<p class="reader-error">PDF 无法载入：${String(error.message||error)}</p>`;
  }
}
