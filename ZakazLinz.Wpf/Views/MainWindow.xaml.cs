using Hardcodet.Wpf.TaskbarNotification;
using System.Windows;
using System.Windows.Resources;
using ZakazLinz.Wpf.Tray;

namespace ZakazLinz.Wpf.Views
{
    public partial class MainWindow : Window
    {
        private TaskbarIcon? _trayIcon;

        public MainWindow()
        {
            InitializeComponent();
            InitializeTray();
        }

        private void InitializeTray()
        {
            // Загружаем TaskbarIcon из ресурсов
            var dict = new ResourceDictionary
            {
                Source = new System.Uri("/ZakazLinz.Wpf;component/Tray/TrayIcon.xaml", System.UriKind.Relative)
            };
            if (dict["AppTrayIcon"] is TaskbarIcon tray)
            {
                _trayIcon = tray;
                _trayIcon.DataContext = new TrayViewModel();
                _trayIcon.Visibility = System.Windows.Visibility.Visible;
            }
        }

        protected override void OnStateChanged(System.EventArgs e)
        {
            base.OnStateChanged(e);
            if (WindowState == WindowState.Minimized)
            {
                Hide();
            }
        }

        protected override void OnClosed(System.EventArgs e)
        {
            base.OnClosed(e);
            _trayIcon?.Dispose();
        }
    }
}