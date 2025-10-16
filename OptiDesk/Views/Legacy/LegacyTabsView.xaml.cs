using System;
using System.Collections.ObjectModel;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using OptiDesk.Data;
using OptiDesk.Models;

namespace OptiDesk.Views.Legacy
{
    public partial class LegacyTabsView : UserControl
    {
        private readonly OptiDeskDbContext _db = new OptiDeskDbContext();

        public ObservableCollection<OrderMKL> OrdersMkl { get; set; } = new();
        public ObservableCollection<OrderMeridian> OrdersMeridian { get; set; } = new();
        public ObservableCollection<PriceItem> Prices { get; set; } = new();

        public LegacyTabsView()
        {
            InitializeComponent();
            _db.Database.EnsureCreated();
            LoadData();
            Unloaded += LegacyTabsView_Unloaded;
        }

        private void LoadData()
        {
            OrdersMkl = new ObservableCollection<OrderMKL>(_db.OrdersMKL.OrderByDescending(o => o.Id).ToList());
            OrdersMeridian = new ObservableCollection<OrderMeridian>(_db.OrdersMeridian.OrderByDescending(o => o.Id).ToList());
            Prices = new ObservableCollection<PriceItem>(_db.PriceItems.OrderByDescending(p => p.Id).ToList());

            OrderMklGrid.ItemsSource = OrdersMkl;
            OrderMeridianGrid.ItemsSource = OrdersMeridian;
            PriceGrid.ItemsSource = Prices;
        }

        // MKL
        private void AddOrderMkl_Click(object sender, RoutedEventArgs e)
        {
            var item = new OrderMKL { Status = "Новый" };
            OrdersMkl.Insert(0, item);
            OrderMklGrid.SelectedItem = item;
            OrderMklGrid.ScrollIntoView(item);
        }

        private void EditOrderMkl_Click(object sender, RoutedEventArgs e)
        {
            if (OrderMklGrid.SelectedItem is not OrderMKL item) return;

            // Попробуем начать редактирование с колонки "Клиент"
            if (OrderMklGrid.Columns.Count > 1)
            {
                OrderMklGrid.Focus();
                var column = OrderMklGrid.Columns[1];
                OrderMklGrid.CurrentCell = new DataGridCellInfo(item, column);
                OrderMklGrid.BeginEdit();
            }
        }

        private void DeleteOrderMkl_Click(object sender, RoutedEventArgs e)
        {
            var selected = OrderMklGrid.SelectedItems.Cast<OrderMKL>().ToList();
            if (selected.Count == 0) return;

            foreach (var s in selected)
            {
                OrdersMkl.Remove(s);
                if (s.Id != 0)
                {
                    _db.OrdersMKL.Remove(s);
                }
            }
            _db.SaveChanges();
        }

        private void SaveOrderMkl_Click(object sender, RoutedEventArgs e)
        {
            foreach (var item in OrdersMkl)
            {
                if (item.Id == 0)
                {
                    _db.OrdersMKL.Add(item);
                }
                else
                {
                    _db.OrdersMKL.Update(item);
                }
            }
            _db.SaveChanges();
            LoadData();
        }

        private void PickClientMkl_Click(object sender, RoutedEventArgs e)
        {
            // Заглушка: позже откроем окно выбора клиента
            MessageBox.Show("Выбор клиента (заглушка). Позже подключим справочник клиентов.", "Клиент", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        private void PickProductMkl_Click(object sender, RoutedEventArgs e)
        {
            // Заглушка: позже откроем окно выбора товара
            MessageBox.Show("Выбор товара (заглушка). Позже подключим справочник товаров/прайсов.", "Товар", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        private void ExportOrderMklTxt_Click(object sender, RoutedEventArgs e)
        {
            var desktop = Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);
            var filePath = Path.Combine(desktop, $"OrdersMKL_{DateTime.Now:yyyyMMdd_HHmmss}.txt");

            var lines = OrdersMkl
                .Select(o => string.Join(';', new[]
                {
                    o.Id.ToString(),
                    o.ClientName ?? "",
                    o.Brand ?? "",
                    o.Sphere?.ToString(CultureInfo.InvariantCulture) ?? "",
                    o.Cylinder?.ToString(CultureInfo.InvariantCulture) ?? "",
                    o.Axis?.ToString(CultureInfo.InvariantCulture) ?? "",
                    o.Status ?? "",
                    o.CreatedAt.ToString("s", CultureInfo.InvariantCulture),
                    o.Comment ?? ""
                }));

            using (var sw = new StreamWriter(filePath, false, System.Text.Encoding.UTF8))
            {
                sw.WriteLine("Id;ClientName;Brand;Sphere;Cylinder;Axis;Status;CreatedAt;Comment");
                foreach (var line in lines)
                {
                    sw.WriteLine(line);
                }
            }

            MessageBox.Show($"Экспорт выполнен:\n{filePath}", "Экспорт TXT", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        // Meridian
        private void AddOrderMeridian_Click(object sender, RoutedEventArgs e)
        {
            var item = new OrderMeridian { Status = "Новый", Supplier = "Меридиан" };
            OrdersMeridian.Insert(0, item);
            OrderMeridianGrid.SelectedItem = item;
            OrderMeridianGrid.ScrollIntoView(item);
        }

        private void DeleteOrderMeridian_Click(object sender, RoutedEventArgs e)
        {
            var selected = OrderMeridianGrid.SelectedItems.Cast<OrderMeridian>().ToList();
            if (selected.Count == 0) return;

            foreach (var s in selected)
            {
                OrdersMeridian.Remove(s);
                if (s.Id != 0)
                {
                    _db.OrdersMeridian.Remove(s);
                }
            }
            _db.SaveChanges();
        }

        private void SaveOrderMeridian_Click(object sender, RoutedEventArgs e)
        {
            foreach (var item in OrdersMeridian)
            {
                if (item.Id == 0)
                {
                    _db.OrdersMeridian.Add(item);
                }
                else
                {
                    _db.OrdersMeridian.Update(item);
                }
            }
            _db.SaveChanges();
            LoadData();
        }

        // Prices
        private void AddPriceItem_Click(object sender, RoutedEventArgs e)
        {
            var item = new PriceItem { SupplierOrBrand = "", Name = "", Price = 0M };
            Prices.Insert(0, item);
            PriceGrid.SelectedItem = item;
            PriceGrid.ScrollIntoView(item);
        }

        private void DeletePriceItem_Click(object sender, RoutedEventArgs e)
        {
            var selected = PriceGrid.SelectedItems.Cast<PriceItem>().ToList();
            if (selected.Count == 0) return;

            foreach (var s in selected)
            {
                Prices.Remove(s);
                if (s.Id != 0)
                {
                    _db.PriceItems.Remove(s);
                }
            }
            _db.SaveChanges();
        }

        private void SavePriceItem_Click(object sender, RoutedEventArgs e)
        {
            foreach (var item in Prices)
            {
                if (item.Id == 0)
                {
                    _db.PriceItems.Add(item);
                }
                else
                {
                    _db.PriceItems.Update(item);
                }
            }
            _db.SaveChanges();
            LoadData();
        }

        private void LegacyTabsView_Unloaded(object sender, RoutedEventArgs e)
        {
            _db.Dispose();
        }
    }
}