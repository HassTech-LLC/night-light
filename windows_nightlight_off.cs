using System;
using System.Diagnostics;
using System.Threading;
using System.Windows.Automation;

namespace NightLightWindowsOff
{
    public class Program
    {
        [STAThread]
        public static int Main()
        {
            try
            {
                // This helper intentionally searches only for the OFF action.
                // It cannot invoke the corresponding ON button.
                Process.Start(new ProcessStartInfo("ms-settings:nightlight") { UseShellExecute = true });
                Thread.Sleep(1800);

                var condition = new PropertyCondition(
                    AutomationElement.AutomationIdProperty,
                    "SystemSettings_Display_BlueLight_ManualToggleOff_Button"
                );
                var button = AutomationElement.RootElement.FindFirst(TreeScope.Descendants, condition);
                if (button == null)
                {
                    Console.WriteLine("ALREADY_OFF: Windows Night Light is not on.");
                    return 0;
                }

                var invoke = button.GetCurrentPattern(InvokePattern.Pattern) as InvokePattern;
                if (invoke == null)
                {
                    Console.WriteLine("ERROR: Windows Night Light off action is unavailable.");
                    return 2;
                }
                invoke.Invoke();
                Console.WriteLine("SUCCESS: Windows Night Light was turned off.");
                return 0;
            }
            catch (Exception ex)
            {
                Console.WriteLine("ERROR: " + ex.Message);
                return 1;
            }
        }
    }
}
