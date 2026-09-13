using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

internal static class ResearchStarterLauncher
{
    [STAThread]
    private static void Main()
    {
        try
        {
            string root = AppDomain.CurrentDomain.BaseDirectory;
            string launcher = Path.Combine(root, "Start Research Starter.cmd");
            if (!File.Exists(launcher))
            {
                throw new FileNotFoundException("Start Research Starter.cmd is missing.", launcher);
            }

            string commandProcessor = Environment.GetEnvironmentVariable("ComSpec") ?? "cmd.exe";
            ProcessStartInfo startInfo = new ProcessStartInfo
            {
                FileName = commandProcessor,
                Arguments = "/d /c \"\"" + launcher + "\"\"",
                WorkingDirectory = root,
                UseShellExecute = false,
                CreateNoWindow = true,
                WindowStyle = ProcessWindowStyle.Hidden
            };
            Process.Start(startInfo);
        }
        catch (Exception error)
        {
            MessageBox.Show(
                "Research Starter could not start.\n\n" + error.Message,
                "Research Starter",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error
            );
        }
    }
}
