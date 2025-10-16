namespace ZakazLinz.Wpf
{
    public partial class App : System.Windows.Application
    {
        public void OnStartup(object sender, System.Windows.StartupEventArgs e)
        {
            var win = new Views.MainWindow
            {
                WindowStartupLocation = System.Windows.WindowStartupLocation.CenterScreen,
                ShowInTaskbar = true
            };
            win.Show();
            win.Activate();
        }
    }
}