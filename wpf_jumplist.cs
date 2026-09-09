using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Shell;

namespace NightLightWpfJumpList
{
    public class Program
    {
        private const string AppId = "Hassan.NightLightWidget.App.1.0";

        [DllImport("shell32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern int SetCurrentProcessExplicitAppUserModelID(string appID);

        private static void AddTask(
            JumpList jumpList,
            string exePath,
            string title,
            string arguments,
            string description)
        {
            jumpList.JumpItems.Add(new JumpTask
            {
                Title = title,
                ApplicationPath = exePath,
                Arguments = arguments,
                Description = description,
                IconResourcePath = exePath,
                IconResourceIndex = 0
            });
        }

        [STAThread]
        public static void Main(string[] args)
        {
            string exePath = args != null && args.Length > 0
                ? Path.GetFullPath(args[0])
                : Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "NightLight.exe");
            string windowsState = args != null && args.Length > 1 ? args[1].ToUpperInvariant() : "UNKNOWN";
            string hassState = args != null && args.Length > 2 ? args[2].ToUpperInvariant() : "UNKNOWN";
            string strength = args != null && args.Length > 3 ? args[3] : "0";

            try
            {
                if (!File.Exists(exePath))
                {
                    throw new FileNotFoundException("NightLight executable was not found.", exePath);
                }

                // Jump Lists are keyed by this ID, which must match the running widget.
                SetCurrentProcessExplicitAppUserModelID(AppId);

                var app = new Application();
                var jumpList = new JumpList();

                AddTask(jumpList, exePath, (windowsState == "UNKNOWN" ? "? " : "✓ ") + "Windows Night Light: " + windowsState, "--show", "Detected Windows Night Light state");
                AddTask(jumpList, exePath, "✓ Night Light: " + hassState, "--show", "Current Night Light filter state");
                AddTask(jumpList, exePath, "Adjust Night Light Warmth...", "--show", "Open the Night Light warmth slider");
                AddTask(jumpList, exePath, (strength == "25" ? "✓ " : "") + "Night Light: 25% (Soft)", "--strength 25", "Set Night Light warmth to 25%");
                AddTask(jumpList, exePath, (strength == "50" ? "✓ " : "") + "Night Light: 50% (Balanced)", "--strength 50", "Set Night Light warmth to 50%");
                AddTask(jumpList, exePath, (strength == "75" ? "✓ " : "") + "Night Light: 75% (Warm)", "--strength 75", "Set Night Light warmth to 75%");
                AddTask(jumpList, exePath, (strength == "100" ? "✓ " : "") + "Night Light: 100% (Maximum)", "--strength 100", "Set Night Light warmth to 100%");
                if (windowsState == "ON")
                {
                    AddTask(jumpList, exePath, "Turn Windows Night Light Off", "--windows-off", "One-way action: this app never turns Windows Night Light on");
                }
                AddTask(jumpList, exePath, "Toggle Night Light", "--toggle", "Turn only the Night Light filter on or off");
                AddTask(jumpList, exePath, "Turn Night Light Off", "--strength 0", "Turn only the Night Light filter off");

                JumpList.SetJumpList(app, jumpList);
                jumpList.Apply();

                Console.WriteLine("SUCCESS: Night Light taskbar JumpList registered.");
            }
            catch (Exception ex)
            {
                Console.WriteLine("ERROR: " + ex);
            }
        }
    }
}
