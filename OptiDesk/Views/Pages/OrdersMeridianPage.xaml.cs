using System.Windows;
using System.Windows.Controls;
using OptiDesk.ViewModels;
using OptiDesk.Views.Dialogs;

namespace OptiDesk.Views.Pages
{
    public partial class OrdersMeridianPage : Page
    {
        private readonly OrdersMeridianViewModel _vm = new OrdersMeridianViewModel();

        public OrdersMeridianPage()
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
            var dlg = new ClientPickerWindow();
            dlg.Owner = Window.GetWindow(this);
            if (dlg.ShowDialog() == true && dlg.Selected != null && _vm.SelectedItem != null)
            {
                _vm.SelectedItem.ClientName = dlg.Selected.Name;
                Grid.Items.Refresh();
            }
        }

        private void PickProduct_Click(object sender, RoutedEventArgs e)
        {
            var dlg = new ProductPickerWindow();
            dlg.Owner = Window.GetWindow(this);
            if (dlg.ShowDialog() == true && dlg.Selected != null && _vm.SelectedItem != null)
            {
                // Для Меридиан заполняем Supplier и LensType
                _vm.SelectedItem.Supplier = dlg.Selected.SupplierOrBrand ?? "Меридиан";
                _vm.SelectedItem.LensType = dlg.Selected.Name ?? "";
                Grid.Items.Refresh();
            }
        }
    }
}