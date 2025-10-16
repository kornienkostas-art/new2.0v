namespace ZakazLinz.Wpf
{
    public partial class App : System.Windows.Application
    {
        protected override void OnStartup(System.Windows.StartupEventArgs e)
        {
            base.OnStartup(e);
            var win = new Views.MainWindow();
            win.WindowStartupLocation = System.Windows.WindowStartupLocation.CenterScreen;
            win.ShowInTaskbar = true;
            win.Show();
            win.Activate();
        }
    }
}