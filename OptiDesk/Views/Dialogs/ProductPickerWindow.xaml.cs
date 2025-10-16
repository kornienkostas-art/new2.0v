using System.Collections.Generic;
using System.Linq;
using System.Windows;
using OptiDesk.Data;
using OptiDesk.Models;

namespace OptiDesk.Views.Dialogs
{
    public partial class ProductPickerWindow : Window
    {
        private readonly OptiDeskDbContext _db = new OptiDeskDbContext();
        private List<PriceItem> _all = new();

        public PriceItem? Selected { get; private set; }

        public ProductPickerWindow()
        {
            InitializeComponent();
            _db.Database.EnsureCreated();
            Load();
        }

        private void Load()
        {
            _all = _db.PriceItems.OrderBy(p => p.SupplierOrBrand).ThenBy(p => p.Name).ToList();
            Grid.ItemsSource = _all;
        }

        private void Search_Click(object sender, RoutedEventArgs e)
        {
            var q = (SearchBox.Text ?? "").Trim().ToLowerInvariant();
            if (string.IsNullOrWhiteSpace(q))
            {
                Grid.ItemsSource = _all;
            }
            else
            {
                Grid.ItemsSource = _all.Where(p =>
                    (p.SupplierOrBrand ?? "").ToLowerInvariant().Contains(q) ||
                    (p.Name ?? "").ToLowerInvariant().Contains(q)).ToList();
            }
        }

        private void Add_Click(object sender, RoutedEventArgs e)
        {
            var dlg = new SimpleProductEditWindow();
            if (dlg.ShowDialog() == true)
            {
                var p = new PriceItem
                {
                    SupplierOrBrand = dlg.SupplierOrBrand,
                    Name = dlg.ProductName,
                    Price = dlg.Price,
                    Note = dlg.Note
                };
                _db.PriceItems.Add(p);
                _db.SaveChanges();
                Load();
            }
        }

        private void Edit_Click(object sender, RoutedEventArgs e)
        {
            if (Grid.SelectedItem is not PriceItem p) return;
            var dlg = new SimpleProductEditWindow(p.SupplierOrBrand, p.Name, p.Price, p.Note);
            if (dlg.ShowDialog() == true)
            {
                p.SupplierOrBrand = dlg.SupplierOrBrand;
                p.Name = dlg.ProductName;
                p.Price = dlg.Price;
                p.Note = dlg.Note;
                _db.PriceItems.Update(p);
                _db.SaveChanges();
                Load();
            }
        }

        private void Delete_Click(object sender, RoutedEventArgs e)
        {
            var selected = Grid.SelectedItems.Cast<PriceItem>().ToList();
            if (selected.Count == 0) return;
            foreach (var p in selected)
            {
                _db.PriceItems.Remove(p);
            }
            _db.SaveChanges();
            Load();
        }

        private void Pick_Click(object sender, RoutedEventArgs e)
        {
            Selected = Grid.SelectedItem as PriceItem;
            if (Selected == null)
            {
                MessageBox.Show("Выберите позицию.", "Внимание", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }
            DialogResult = true;
        }

        private void Cancel_Click(object sender, RoutedEventArgs e)
        {
            DialogResult = false;
        }
    }
}