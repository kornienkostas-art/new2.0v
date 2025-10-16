using System.IO;
using System.Text.Json;
using ZakazLinz.Wpf.Models;

namespace ZakazLinz.Wpf.Services
{
    public class SettingsService
    {
        private readonly string _path;

        public SettingsService()
        {
            var exeDir = AppContext.BaseDirectory;
            _path = Path.Combine(exeDir, "settings.json");
        }

        public Settings Load()
        {
            if (!File.Exists(_path))
                return new Settings();

            var json = File.ReadAllText(_path);
            var s = JsonSerializer.Deserialize<Settings>(json);
            return s ?? new Settings();
        }

        public void Save(Settings settings)
        {
            var json = JsonSerializer.Serialize(settings, new JsonSerializerOptions
            {
                WriteIndented = true
            });
            File.WriteAllText(_path, json);
        }
    }
}