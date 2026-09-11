// Embedded, local-only WebView2 shell. Only the parent owns the display engine.
using System;
using System.IO;
using System.Drawing;
using System.Windows.Forms;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;
using System.Collections.Generic;
using System.Runtime.InteropServices;

class PremiumHost : Form {
    [DllImport("gdi32.dll")] static extern IntPtr CreateRoundRectRgn(int l,int t,int r,int b,int w,int h);
    [DllImport("gdi32.dll")] static extern bool DeleteObject(IntPtr region);
    [DllImport("user32.dll")] static extern bool ReleaseCapture();
    [DllImport("user32.dll")] static extern IntPtr SendMessage(IntPtr h,int m,IntPtr w,IntPtr l);
    [DllImport("user32.dll")] static extern bool SetProcessDpiAwarenessContext(IntPtr value);
    readonly WebView2 view = new WebView2();
    readonly JavaScriptSerializer json = new JavaScriptSerializer();
    bool quitting;
    bool ready;
    const string Origin = "https://nightlight.local";
    readonly string assets;
    readonly string profile;
    readonly string capture;
    public PremiumHost(string[] args) {
        assets = Path.GetFullPath(args[0]); profile = Path.GetFullPath(args[1]);
        capture = args.Length > 2 ? Path.GetFullPath(args[2]) : null;
        Text = "Night Light by HT";
        FormBorderStyle = FormBorderStyle.None;
        ClientSize = new Size(416, 820); MinimumSize = new Size(350, 500);
        AutoScaleMode = AutoScaleMode.Dpi; BackColor = Color.FromArgb(24,30,39);
        StartPosition = FormStartPosition.Manual;
        var area = Screen.FromPoint(Cursor.Position).WorkingArea;
        Height = Math.Min(Height, area.Height - 24);
        Location = new Point(area.Right - Width - 16, area.Bottom - Height - 12);
        var icon = Path.Combine(assets,"..","app.ico");
        if (File.Exists(icon)) Icon = new Icon(icon);
        view.Dock = DockStyle.Fill; Controls.Add(view);
        Resize += (s,e) => { if(WindowState==FormWindowState.Minimized) Emit("hidden"); else RoundWindow(); };
        RoundWindow();
        Shown += async (s,e) => await Initialize();
        FormClosing += (s,e) => { if (!quitting) { e.Cancel=true; Hide(); Emit("hidden"); } };
    }
    void Emit(string kind) { Console.WriteLine(json.Serialize(new {kind=kind})); Console.Out.Flush(); }
    void RoundWindow() {
        int diameter;
        using(var graphics=CreateGraphics()) diameter=(int)(56*graphics.DpiX/96);
        IntPtr region=CreateRoundRectRgn(0,0,Width+1,Height+1,diameter,diameter);
        var old=Region;Region=Region.FromHrgn(region);DeleteObject(region);if(old!=null)old.Dispose();
    }
    async Task Initialize() {
        try {
            var options = new CoreWebView2EnvironmentOptions();
            int port;
            if (Environment.GetEnvironmentVariable("NIGHT_LIGHT_BY_HT_DISABLE_DISPLAY_BACKEND")=="1" && Int32.TryParse(Environment.GetEnvironmentVariable("NIGHT_LIGHT_PREMIUM_TEST_PORT"),out port) && port>=1024 && port<=65535)
                options.AdditionalBrowserArguments="--remote-debugging-port="+port;
            var env = await CoreWebView2Environment.CreateAsync(null, profile, options);
            await view.EnsureCoreWebView2Async(env);
            var core = view.CoreWebView2;
            core.Settings.AreDevToolsEnabled = false;
            core.Settings.AreDefaultContextMenusEnabled = false;
            core.Settings.IsStatusBarEnabled = false;
            core.Settings.AreHostObjectsAllowed = false;
            core.SetVirtualHostNameToFolderMapping("nightlight.local",assets,CoreWebView2HostResourceAccessKind.DenyCors);
            core.NavigationStarting += (s,e) => { if (e.Uri != Origin+"/index.html") e.Cancel=true; };
            core.NewWindowRequested += (s,e) => e.Handled=true;
            core.PermissionRequested += (s,e) => e.State=CoreWebView2PermissionState.Deny;
            core.DownloadStarting += (s,e) => e.Cancel=true;
            core.WebMessageReceived += (s,e) => {
                if (e.Source != Origin+"/index.html") return;
                string message=e.WebMessageAsJson;
                if (message.Length>16384) return;
                var request=json.Deserialize<Dictionary<string,object>>(message);
                object action;
                if(request.TryGetValue("action",out action)) {
                    if((action as string)=="drag") { ReleaseCapture();SendMessage(Handle,0xA1,(IntPtr)2,IntPtr.Zero);return; }
                    if((action as string)=="minimize") { WindowState=FormWindowState.Minimized;return; }
                }
                Console.WriteLine(message); Console.Out.Flush();
            };
            core.NavigationCompleted += async (s,e) => {
                if (!e.IsSuccess) { Emit("failed"); return; }
                ready=true; Emit("ready");
                if (capture!=null) {
                    await Task.Delay(1800);
                    using(var stream=File.Create(capture)) await core.CapturePreviewAsync(CoreWebView2CapturePreviewImageFormat.Png,stream);
                    Emit("captured");
                }
            };
            core.ProcessFailed += (s,e) => { Emit("failed"); };
            core.Navigate(Origin+"/index.html");
            await Task.Run(() => {
                string line;
                while ((line=Console.ReadLine())!=null) {
                    if (line.Length>65536) continue;
                    string command=line;
                    try { BeginInvoke((Action)(()=>Receive(command))); } catch { break; }
                }
                try { BeginInvoke((Action)(()=>{quitting=true;Close();})); } catch {}
            });
        } catch (Exception) {
            Emit("failed");
            MessageBox.Show("The premium interface could not start. Install or repair Microsoft Edge WebView2 Runtime. Your tray controls and emergency reset remain available.","Night Light",MessageBoxButtons.OK,MessageBoxIcon.Warning);
            quitting=true; Close();
        }
    }
    void Receive(string line) {
        try {
            var data=json.Deserialize<Dictionary<string,object>>(line);
            var kind=data["kind"] as string;
            if (kind=="show") { Show(); WindowState=FormWindowState.Normal; Activate(); Emit("shown"); }
            else if (kind=="hide") { Hide(); Emit("hidden"); }
            else if (kind=="close") { quitting=true;Close(); }
            else if (ready && (kind=="state" || kind=="lookup" || kind=="error")) view.CoreWebView2.PostWebMessageAsJson(line);
        } catch { Emit("protocol_error"); }
    }
    [STAThread] static void Main(string[] args) {
        if(args.Length<2) return;
        // WebView2 uses a child HWND. Without per-monitor-v2 awareness the
        // child can be positioned in physical pixels while this host is still
        // DPI-virtualized, leaving a blank shell on mixed-scale displays.
        SetProcessDpiAwarenessContext(new IntPtr(-4));
        // A GUI process has pipes, not a console. Setting Console.InputEncoding
        // calls SetConsoleCP and fails with ERROR_INVALID_HANDLE in the bundle.
        Console.SetIn(new StreamReader(Console.OpenStandardInput(),new System.Text.UTF8Encoding(false)));
        Console.SetOut(new StreamWriter(Console.OpenStandardOutput(),new System.Text.UTF8Encoding(false)) { AutoFlush=true });
        Application.EnableVisualStyles(); Application.SetCompatibleTextRenderingDefault(false);
        Application.Run(new PremiumHost(args));
    }
}
