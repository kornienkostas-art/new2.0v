namespace ZakazLinz.Wpf
{
    public partial class App : System.Windows.Application
    {
        public void OnStartup(object sender, System.Windows.StartupEventArgs e)
        {
            try
            {
                var win = new Views.MainWindow
                {
                    WindowStartupLocation = System.Windows.WindowStartupLocation.CenterScreen,
                    ShowInTaskbar = true
                };

                // Назначаем основное окно и режим завершения
                this.MainWindow = win;
                this.ShutdownMode = System.Windows.ShutdownMode.OnMainWindowClose;

                win.Show();
                win.Activate();
            }
            catch (System.Exception ex)
            {
                System.Windows.MessageBox.Show("Ошибка запуска: " + ex.Message, "ZakazLinz.Wpf", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Error);
                // На всякий случай не оставляем процесс висеть
                this.Shutdown();
            }
        }
    }
}