using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Hardcodet.Wpf.TaskbarNotification;
using ZakazLinz.Wpf.Services;

namespace ZakazLinz.Wpf.Tray
{
    public partial class TrayViewModel : ObservableObject
    {
        private readonly AutostartService _autostartService;

        [ObservableProperty] private bool isAutostartEnabled;

        public IRelayCommand OpenMainCommand { get; }
        public IRelayCommand OpenSettingsCommand { get; }
        public IRelayCommand ToggleAutostartCommand { get; }
        public IRelayCommand ExitCommand { get; }

        public TrayViewModel()
        {
            _autostartService = new AutostartService();
            isAutostartEnabled = _autostartService.IsEnabled();

            OpenMainCommand = new RelayCommand(OpenMain);
            OpenSettingsCommand = new RelayCommand(OpenSettings);
            ToggleAutostartCommand = new RelayCommand(ToggleAutostart);
            ExitCommand = new RelayCommand(() => System.Windows.Application.Current.Shutdown());
        }

        private void OpenMain()
        {
            var win = System.Windows.Application.Current.MainWindow;
            if (win != null)
            {
                win.Show();
                win.WindowState = System.Windows.WindowState.Normal;
                win.Activate();
            }
        }

        private void OpenSettings()
        {
            OpenMain();
            // Дополнительно можно переключить вкладку на настройки через общий сервис/мессенджер
        }

        private void ToggleAutostart()
        {
            if (IsAutostartEnabled) _autostartService.Disable();
            else _autostartService.Enable();

            IsAutostartEnabled = _autostartService.IsEnabled();
        }
    }
}