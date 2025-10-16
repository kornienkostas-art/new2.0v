using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using System.Windows.Controls;

namespace ZakazLinz.Wpf.Views
{
    public partial class MainWindowViewModel : ObservableObject
    {
        [ObservableProperty] private UserControl? currentView;
        [ObservableProperty] private string statusText = "Готово";

        public IRelayCommand OpenMklOrdersCommand { get; }
        public IRelayCommand OpenMeridianOrdersCommand { get; }
        public IRelayCommand OpenSettingsCommand { get; }

        public MainWindowViewModel()
        {
            OpenMklOrdersCommand = new RelayCommand(OpenMklOrders);
            OpenMeridianOrdersCommand = new RelayCommand(OpenMeridianOrders);
            OpenSettingsCommand = new RelayCommand(OpenSettings);

            // Начальный экран
            OpenMklOrders();
        }

        private void OpenMklOrders()
        {
            CurrentView = new OrdersMklView();
            StatusText = "Заказы МКЛ";
        }

        private void OpenMeridianOrders()
        {
            CurrentView = new OrdersMeridianView();
            StatusText = "Заказы «Меридиан»";
        }

        private void OpenSettings()
        {
            CurrentView = new SettingsView();
            StatusText = "Настройки";
        }
    }
}