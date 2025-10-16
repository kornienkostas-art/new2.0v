using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Microsoft.Win32;
using System.IO;
using System.Windows.Forms;
using ZakazLinz.Wpf.Services;

namespace ZakazLinz.Wpf.ViewModels
{
    public partial class SettingsViewModel : ObservableObject
    {
        private readonly SettingsService _settingsService;
        private readonly AutostartService _autostartService;

        [ObservableProperty] private int uiScalePercent;
        [ObservableProperty] private int fontSize;
        [ObservableProperty] private string exportFolder = "";
        [ObservableProperty] private bool enableTray;
        [ObservableProperty] private bool enableNotifications;
        [ObservableProperty] private bool enableAutostart;

        public IRelayCommand SaveCommand { get; }
        public IRelayCommand ReloadCommand { get; }
        public IRelayCommand BrowseExportFolderCommand { get; }

        public SettingsViewModel()
        {
            _settingsService = new SettingsService();
            _autostartService = new AutostartService();

            Load();
            SaveCommand = new RelayCommand(Save);
            ReloadCommand = new RelayCommand(Load);
            BrowseExportFolderCommand = new RelayCommand(BrowseExportFolder);
        }

        private void Load()
        {
            var s = _settingsService.Load();
            uiScalePercent = s.UiScalePercent;
            fontSize = s.FontSize;
            exportFolder = s.ExportFolder ?? "";
            enableTray = s.EnableTray;
            enableNotifications = s.EnableNotifications;
            enableAutostart = _autostartService.IsEnabled();
            OnPropertyChanged(string.Empty);
        }

        private void Save()
        {
            _settingsService.Save(new Models.Settings
            {
                UiScalePercent = uiScalePercent,
                FontSize = fontSize,
                ExportFolder = exportFolder,
                EnableTray = enableTray,
                EnableNotifications = enableNotifications
            });

            if (enableAutostart)
                _autostartService.Enable();
            else
                _autostartService.Disable();
        }

        private void BrowseExportFolder()
        {
            using var dialog = new FolderBrowserDialog();
            dialog.Description = "Выберите папку для экспорта";
            dialog.ShowNewFolderButton = true;
            if (dialog.ShowDialog() == DialogResult.OK)
            {
                ExportFolder = dialog.SelectedPath;
            }
        }
    }
}