using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.FileProviders;
using Microsoft.Extensions.Hosting;
using System.IO;

var builder = WebApplication.CreateBuilder(args);

// Add API controllers
builder.Services.AddControllers();
builder.Services.AddControllers().AddJsonOptions(options =>
{
    options.JsonSerializerOptions.PropertyNamingPolicy = null;
});

var app = builder.Build();

// Path candidates for Blazor wwwroot
var publishSpaPath = Path.Combine(builder.Environment.ContentRootPath, "..", "MonumentGameWeb", "publish", "wwwroot");
var devSpaPath = Path.Combine(builder.Environment.ContentRootPath, "..", "MonumentGameWeb", "wwwroot");

// Prefer published folder, fallback to dev wwwroot
var spaPath = Directory.Exists(publishSpaPath) ? publishSpaPath : devSpaPath;

if (!Directory.Exists(spaPath))
{
    throw new DirectoryNotFoundException($"Blazor wwwroot folder not found at {spaPath}");
}

// Serve static files
app.UseDefaultFiles(new DefaultFilesOptions { FileProvider = new PhysicalFileProvider(spaPath) });
app.UseStaticFiles(new StaticFileOptions { FileProvider = new PhysicalFileProvider(spaPath), RequestPath = "" });

app.UseRouting();

// Map API endpoints
app.MapControllers();

// SPA fallback
app.MapFallbackToFile("index.html");

app.Run();
