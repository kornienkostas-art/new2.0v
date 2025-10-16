namespace ZakazLinz.Wpf.Models
{
    public class Settings
    {
        public int UiScalePercent { get; set; } = 100;
        public int FontSize { get; set; } = 14;
        public string? ExportFolder { get; set; } = null;
        public bool EnableTray { get; set; } = true;
        public bool EnableNotifications { get; set; } = true;
    }
}