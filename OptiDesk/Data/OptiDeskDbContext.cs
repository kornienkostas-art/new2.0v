using Microsoft.EntityFrameworkCore;
using OptiDesk.Models;
using System;
using System.IO;

namespace OptiDesk.Data
{
    public class OptiDeskDbContext : DbContext
    {
        public DbSet<OrderMKL> OrdersMKL { get; set; } = null!;
        public DbSet<OrderMeridian> OrdersMeridian { get; set; } = null!;
        public DbSet<PriceItem> PriceItems { get; set; } = null!;

        protected override void OnConfiguring(DbContextOptionsBuilder optionsBuilder)
        {
            // Store DB in local AppData\OptiDesk\opti.db
            var appData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            var dir = Path.Combine(appData, "OptiDesk");
            if (!Directory.Exists(dir))
            {
                Directory.CreateDirectory(dir);
            }
            var dbPath = Path.Combine(dir, "opti.db");
            optionsBuilder.UseSqlite($"Data Source={dbPath}");
        }

        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            modelBuilder.Entity<OrderMKL>().Property(p => p.Sphere).HasPrecision(6, 2);
            modelBuilder.Entity<OrderMKL>().Property(p => p.Cylinder).HasPrecision(6, 2);

            modelBuilder.Entity<PriceItem>().Property(p => p.Price).HasPrecision(10, 2);
        }
    }
}