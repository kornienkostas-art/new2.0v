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
            try
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
                    // Задаём системную иконку, чтобы не падать без ресурсов
                    _trayIcon.Icon = System.Drawing.SystemIcons.Application;
                    _trayIcon.Visibility = System.Windows.Visibility.Visible;
                }
            }
            catch
            {
                // Если трей не инициализировался, продолжаем работу окна
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