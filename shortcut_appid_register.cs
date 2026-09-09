using System;
using System.Runtime.InteropServices;

namespace NightLightShortcutAppId
{
    [ComImport]
    [Guid("00021401-0000-0000-C000-000000000046")]
    [ClassInterface(ClassInterfaceType.None)]
    internal class ShellLinkClass { }

    [ComImport]
    [Guid("000214F9-0000-0000-C000-000000000046")]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    internal interface IShellLinkW { }

    [ComImport]
    [Guid("0000010b-0000-0000-C000-000000000046")]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    internal interface IPersistFile
    {
        void GetClassID(out Guid pClassID);
        void IsDirty();
        void Load([MarshalAs(UnmanagedType.LPWStr)] string pszFileName, uint dwMode);
        void Save([MarshalAs(UnmanagedType.LPWStr)] string pszFileName, bool fRemember);
        void SaveCompleted([MarshalAs(UnmanagedType.LPWStr)] string pszFileName);
        void GetCurFile([MarshalAs(UnmanagedType.LPWStr)] out string ppszFileName);
    }

    [ComImport]
    [Guid("886d8eeb-8cf2-4446-8d02-cdba1dbdcf99")]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    internal interface IPropertyStore
    {
        void GetCount(out uint cProps);
        void GetAt(uint iProp, IntPtr pkey);
        void GetValue(IntPtr key, IntPtr pv);
        void SetValue(ref PropertyKey key, ref PropVariant propvar);
        void Commit();
    }

    [StructLayout(LayoutKind.Sequential, Pack = 4)]
    internal struct PropertyKey
    {
        public Guid fmtid;
        public uint pid;

        public PropertyKey(Guid guid, uint id)
        {
            fmtid = guid;
            pid = id;
        }
    }

    [StructLayout(LayoutKind.Explicit)]
    internal struct PropVariant
    {
        [FieldOffset(0)] public ushort vt;
        [FieldOffset(8)] public IntPtr pwszVal;

        public static PropVariant FromString(string value)
        {
            return new PropVariant
            {
                vt = 31, // VT_LPWSTR
                pwszVal = Marshal.StringToCoTaskMemUni(value)
            };
        }
    }

    public class Program
    {
        private const uint StgmReadWrite = 0x00000002;
        private const uint ShcneUpdateItem = 0x00002000;
        private const uint ShcnfPathW = 0x0005;
        private static readonly PropertyKey AppUserModelIdKey = new PropertyKey(
            new Guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"), 5);

        [DllImport("shell32.dll", CharSet = CharSet.Unicode)]
        private static extern void SHChangeNotify(uint wEventId, uint uFlags, string dwItem1, IntPtr dwItem2);

        public static void Main(string[] args)
        {
            if (args == null || args.Length < 2)
            {
                Console.WriteLine("USAGE: shortcut_appid_register.exe <shortcut.lnk> <app-id>");
                return;
            }

            string shortcutPath = args[0];
            string appId = args[1];
            try
            {
                var link = (IShellLinkW)new ShellLinkClass();
                var persistFile = (IPersistFile)link;
                persistFile.Load(shortcutPath, StgmReadWrite);

                var propertyStore = (IPropertyStore)link;
                var value = PropVariant.FromString(appId);
                var appUserModelIdKey = AppUserModelIdKey;
                try
                {
                    propertyStore.SetValue(ref appUserModelIdKey, ref value);
                    propertyStore.Commit();
                    persistFile.Save(shortcutPath, true);
                }
                finally
                {
                    if (value.pwszVal != IntPtr.Zero)
                    {
                        Marshal.FreeCoTaskMem(value.pwszVal);
                    }
                }

                SHChangeNotify(ShcneUpdateItem, ShcnfPathW, shortcutPath, IntPtr.Zero);
                Console.WriteLine("SUCCESS: AppUserModelID set for " + shortcutPath);
            }
            catch (Exception ex)
            {
                Console.WriteLine("ERROR: " + ex);
                Environment.ExitCode = 1;
            }
        }
    }
}
