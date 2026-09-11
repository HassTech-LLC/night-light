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
            string smartState = args != null && args.Length > 2 ? args[2].ToUpperInvariant() : "OFF";

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

                AddTask(jumpList, exePath, "Open Night Light", "--show", "Open controls, schedule and appearance");
                if (smartState == "ACTIVE")
                    AddTask(jumpList, exePath, "Pause Smart for 1 hour", "--pause-smart", "Restore original colors for one hour, then resume your schedule");
                else if (smartState == "PAUSED")
                    AddTask(jumpList, exePath, "Resume Smart", "--resume-smart", "End the temporary override and follow your schedule");
                AddTask(jumpList, exePath, "Warmth: Soft (25%)", "--strength 25", "Set warmth to 25%; temporarily overrides Smart for one hour");
                AddTask(jumpList, exePath, "Warmth: Medium (50%)", "--strength 50", "Set warmth to 50%; temporarily overrides Smart for one hour");
                AddTask(jumpList, exePath, "Warmth: Warm (75%)", "--strength 75", "Set warmth to 75%; temporarily overrides Smart for one hour");
                AddTask(jumpList, exePath, "Warmth: Maximum (100%)", "--strength 100", "Set warmth to 100%; temporarily overrides Smart for one hour");
                if (windowsState == "ON")
                {
                    AddTask(jumpList, exePath, "Turn Windows Night Light Off", "--windows-off", "One-way action: this app never turns Windows Night Light on");
                }
                AddTask(jumpList, exePath, "Turn filter off", "--strength 0", "Restore original colors and stop Smart until you enable it again");

                JumpList.SetJumpList(app, jumpList);
                jumpList.Apply();

                Console.WriteLine("SUCCESS: Night Light taskbar JumpList registered.");
            }
            catch (Exception ex)
            {
                Console.WriteLine("ERROR: " + ex);
                Environment.ExitCode = 1;
            }
        }
    }
}
