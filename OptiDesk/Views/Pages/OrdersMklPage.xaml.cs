using System.Windows;
using System.Windows.Controls;
using OptiDesk.ViewModels;

namespace OptiDesk.Views.Pages
{
    public partial class OrdersMklPage : Page
    {
        private readonly OrdersMklViewModel _vm = new OrdersMklViewModel();

        public OrdersMklPage()
        {
            InitializeComponent();
            DataContext = _vm;
        }

        private void New_Click(object sender, RoutedEventArgs e)
        {
            _vm.AddNew();
            if (_vm.SelectedItem != null)
            {
                Grid.SelectedItem = _vm.SelectedItem;
                Grid.ScrollIntoView(_vm.SelectedItem);
            }
        }

        private void Edit_Click(object sender, RoutedEventArgs e)
        {
            if (_vm.SelectedItem == null) return;
            if (Grid.Columns.Count > 1)
            {
                Grid.Focus();
                var column = Grid.Columns[1]; // Клиент
                Grid.CurrentCell = new DataGridCellInfo(_vm.SelectedItem, column);
                Grid.BeginEdit();
            }
        }

        private void Delete_Click(object sender, RoutedEventArgs e)
        {
            _vm.DeleteSelected(Grid.SelectedItems);
        }

        private void Save_Click(object sender, RoutedEventArgs e)
        {
            _vm.SaveAll();
        }

        private void Export_Click(object sender, RoutedEventArgs e)
        {
            var path = _vm.ExportTxt();
            MessageBox.Show($"Экспорт выполнен:\n{path}", "Экспорт TXT", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        private void PickClient_Click(object sender, RoutedEventArgs e)
        {
            MessageBox.Show("Выбор клиента (заглушка).", "Клиент", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        private void PickProduct_Click(object sender, RoutedEventArgs e)
        {
            MessageBox.Show("Выбор товара (заглушка).", "Товар", MessageBoxButton.OK, MessageBoxImage.Information);
        }
    }
}