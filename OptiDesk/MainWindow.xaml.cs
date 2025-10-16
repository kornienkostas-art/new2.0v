using System.Windows;
using OptiDesk.Views.Legacy;
using OptiDesk.Views.Pages;

namespace OptiDesk
{
    public partial class MainWindow : Window
    {
        public MainWindow()
        {
            InitializeComponent();
            // Default content: legacy tabs to preserve current functionality
            MainFrame.Content = new LegacyTabsView();
        }

        private void OpenLegacy_Click(object sender, RoutedEventArgs e)
        {
            MainFrame.Content = new LegacyTabsView();
        }

        private void OpenOrdersMkl_Click(object sender, RoutedEventArgs e)
        {
            MainFrame.Content = new OrdersMklPage();
        }

        private void OpenOrdersMeridian_Click(object sender, RoutedEventArgs e)
        {
            MainFrame.Content = new OrdersMeridianPage();
        }

        private void OpenPrices_Click(object sender, RoutedEventArgs e)
        {
            MainFrame.Content = new PricesPage();
        }

        private void OpenSettings_Click(object sender, RoutedEventArgs e)
        {
            MainFrame.Content = new SettingsPage();
        }
    }
}