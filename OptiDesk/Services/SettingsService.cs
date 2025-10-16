using System;
using System.IO;
using System.Text.Json;

namespace OptiDesk.Services
{
    public class AppSettings
    {
        public string? ExportFolder { get; set; }
        public bool UseTray { get; set; } = false;
        public bool MinimizeToTray { get; set; } = true;
        public bool EnableNotifications { get; set; } = false;
    }

    public static class SettingsService
    {
        private static readonly string BaseDir = AppDomain.CurrentDomain.BaseDirectory;
        private static readonly string SettingsPath = Path.Combine(BaseDir, "settings.json");

        private static AppSettings? _cached;

        public static AppSettings Load()
        {
            if (_cached is not null) return _cached;

            try
            {
                if (File.Exists(SettingsPath))
                {
                    var json = File.ReadAllText(SettingsPath);
                    _cached = JsonSerializer.Deserialize<AppSettings>(json) ?? new AppSettings();
                }
                else
                {
                    _cached = new AppSettings();
                }
            }
            catch
            {
                _cached = new AppSettings();
            }

            // Default export folder = Desktop if not specified
            if (string.IsNullOrWhiteSpace(_cached!.ExportFolder))
            {
                _cached.ExportFolder = Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);
            }

            return _cached;
        }

        public static void Save(AppSettings settings)
        {
            _cached = settings;
            var json = JsonSerializer.Serialize(settings, new JsonSerializerOptions { WriteIndented = true });
            File.WriteAllText(SettingsPath, json);
        }
    }
}