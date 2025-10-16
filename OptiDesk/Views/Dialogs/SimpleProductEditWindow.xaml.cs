using System;
using System.Globalization;
using System.Windows;

namespace OptiDesk.Views.Dialogs
{
    public partial class SimpleProductEditWindow : Window
    {
        public string SupplierOrBrand => SupplierBox.Text.Trim();
        public string ProductName => NameBox.Text.Trim();

        public decimal Price
        {
            get
            {
                if (decimal.TryParse(PriceBox.Text.Trim(), NumberStyles.Any, CultureInfo.InvariantCulture, out var v))
                    return v;
                if (decimal.TryParse(PriceBox.Text.Trim(), NumberStyles.Any, CultureInfo.CurrentCulture, out v))
                    return v;
                return 0m;
            }
        }

        public string? Note => NoteBox.Text.Trim();

        public SimpleProductEditWindow(string? supplier = null, string? name = null, decimal? price = null, string? note = null)
        {
            InitializeComponent();
            SupplierBox.Text = supplier ?? "";
            NameBox.Text = name ?? "";
            PriceBox.Text = (price ?? 0m).ToString(CultureInfo.InvariantCulture);
            NoteBox.Text = note ?? "";
        }

        private void Ok_Click(object sender, RoutedEventArgs e)
        {
            if (string.IsNullOrWhiteSpace(SupplierOrBrand) || string.IsNullOrWhiteSpace(ProductName))
            {
                MessageBox.Show("Заполните поставщика и наименование.", "Внимание", MessageBoxButton.OK, MessageBoxImage.Warning);
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