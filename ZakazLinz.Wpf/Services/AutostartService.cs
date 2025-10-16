using Microsoft.Win32;

namespace ZakazLinz.Wpf.Services
{
    public class AutostartService
    {
        private const string RunKey = "Software\\Microsoft\\Windows\\CurrentVersion\\Run";
        private const string AppName = "UssurochkiRF";

        public void Enable()
        {
            using var key = Registry.CurrentUser.OpenSubKey(RunKey, writable: true);
            var exePath = System.Diagnostics.Process.GetCurrentProcess().MainModule?.FileName ?? "";
            key?.SetValue(AppName, exePath);
        }

        public void Disable()
        {
            using var key = Registry.CurrentUser.OpenSubKey(RunKey, writable: true);
            key?.DeleteValue(AppName, false);
        }

        public bool IsEnabled()
        {
            using var key = Registry.CurrentUser.OpenSubKey(RunKey, writable: false);
            var value = key?.GetValue(AppName) as string;
            return !string.IsNullOrEmpty(value);
        }
    }
}