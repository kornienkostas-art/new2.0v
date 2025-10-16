namespace OptiDesk.Models
{
    public class PriceItem
    {
        public int Id { get; set; }
        public string SupplierOrBrand { get; set; } = string.Empty;
        public string Name { get; set; } = string.Empty;
        public decimal Price { get; set; }
        public string? Note { get; set; }
    }
}