using System;
using System.IO;
using System.Runtime.InteropServices;

namespace NightLightJumpList
{
    [ComImport]
    [Guid("86c27970-d729-4261-ac5c-569264c344ee")]
    [ClassInterface(ClassInterfaceType.None)]
    public class DestinationListClass { }

    [ComImport]
    [Guid("2d3436c2-9421-4286-82d5-60a6efd72346")]
    [ClassInterface(ClassInterfaceType.None)]
    public class EnumerableObjectCollectionClass { }

    [ComImport]
    [Guid("00021401-0000-0000-C000-000000000046")]
    [ClassInterface(ClassInterfaceType.None)]
    public class ShellLinkClass { }

    [ComImport]
    [Guid("6332debf-87b5-4670-90c0-5e57b408a49e")]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    public interface ICustomDestinationList
    {
        void SetAppID([MarshalAs(UnmanagedType.LPWStr)] string pszAppID);
        void BeginList(out uint pcMinSlots, [In] ref Guid riid, [MarshalAs(UnmanagedType.IUnknown)] out object ppv);
        void AppendCategory([MarshalAs(UnmanagedType.LPWStr)] string pszCategory, [MarshalAs(UnmanagedType.IUnknown)] object poa);
        void AppendKnownCategory(int category);
        void AddUserTasks([MarshalAs(UnmanagedType.IUnknown)] object poa);
        void CommitList();
        void GetRemovedDestinations([In] ref Guid riid, [MarshalAs(UnmanagedType.IUnknown)] out object ppv);
        void DeleteList([MarshalAs(UnmanagedType.LPWStr)] string pszAppID);
        void AbortList();
    }

    [ComImport]
    [Guid("5632b1a5-e38a-400a-928a-d4cd63230295")]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    public interface IObjectCollection
    {
        void AddObject([MarshalAs(UnmanagedType.IUnknown)] object punk);
        void AddFromArray(object poaSource);
        void RemoveObjectAt(uint uiIndex);
        void Clear();
    }

    [ComImport]
    [Guid("000214F9-0000-0000-C000-000000000046")]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    public interface IShellLinkW
    {
        void GetPath([Out, MarshalAs(UnmanagedType.LPWStr)] System.Text.StringBuilder pszFile, int cchMaxPath, IntPtr pfd, uint fFlags);
        void GetIDList(out IntPtr ppidl);
        void SetIDList(IntPtr pidl);
        void GetDescription([Out, MarshalAs(UnmanagedType.LPWStr)] System.Text.StringBuilder pszName, int cchMaxName);
        void SetDescription([MarshalAs(UnmanagedType.LPWStr)] string pszName);
        void GetWorkingDirectory([Out, MarshalAs(UnmanagedType.LPWStr)] System.Text.StringBuilder pszDir, int cchMaxPath);
        void SetWorkingDirectory([MarshalAs(UnmanagedType.LPWStr)] string pszDir);
        void GetArguments([Out, MarshalAs(UnmanagedType.LPWStr)] System.Text.StringBuilder pszArgs, int cchMaxPath);
        void SetArguments([MarshalAs(UnmanagedType.LPWStr)] string pszArgs);
        void GetHotkey(out short pwHotkey);
        void SetHotkey(short wHotkey);
        void GetShowCmd(out int piShowCmd);
        void SetShowCmd(int iShowCmd);
        void GetIconLocation([Out, MarshalAs(UnmanagedType.LPWStr)] System.Text.StringBuilder pszIconPath, int cchIconPath, out int piIcon);
        void SetIconLocation([MarshalAs(UnmanagedType.LPWStr)] string pszIconPath, int iIcon);
        void SetRelativePath([MarshalAs(UnmanagedType.LPWStr)] string pszPathRel, uint dwReserved);
        void Resolve(IntPtr hwnd, uint fFlags);
        void SetPath([MarshalAs(UnmanagedType.LPWStr)] string pszFile);
    }

    [ComImport]
    [Guid("886d8eeb-8cf2-4446-8d02-cdba1dbdcf99")]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    public interface IPropertyStore
    {
        void GetCount(out uint cProps);
        void GetAt(uint iProp, IntPtr pkey);
        void GetValue(IntPtr key, IntPtr pv);
        void SetValue(ref PropertyKey key, ref PropVariant propvar);
        void Commit();
    }

    [StructLayout(LayoutKind.Sequential, Pack = 4)]
    public struct PropertyKey
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
    public struct PropVariant
    {
        [FieldOffset(0)] public ushort vt;
        [FieldOffset(8)] public IntPtr pwszVal;

        public static PropVariant FromString(string val)
        {
            PropVariant pv = new PropVariant();
            pv.vt = 31; // VT_LPWSTR
            pv.pwszVal = Marshal.StringToCoTaskMemUni(val);
            return pv;
        }
    }

    public class Program
    {
        public static void Main(string[] args)
        {
            string appId = args.Length > 0 ? args[0] : "Hassan.NightLightWidget.App.1.0";
            string exePath = args.Length > 1
                ? args[1]
                : Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "NightLight.exe");

            try
            {
                var destList = (ICustomDestinationList)new DestinationListClass();
                destList.SetAppID(appId);

                uint minSlots;
                Guid iidObjectArray = new Guid("92CA9DCD-5622-4bba-A805-5E9F541BD8C9");
                object removed;
                destList.BeginList(out minSlots, ref iidObjectArray, out removed);

                var collection = (IObjectCollection)new EnumerableObjectCollectionClass();
                var pkeyTitle = new PropertyKey(new Guid("F29F85E0-4FF9-1068-AB91-08002B27B3D9"), 2); // PKEY_Title

                // Task 1: Adjust Strength (Slider)
                var link1 = (IShellLinkW)new ShellLinkClass();
                link1.SetPath(exePath);
                link1.SetArguments("--show");
                link1.SetDescription("Open Night Light Strength slider");
                link1.SetIconLocation(exePath, 0);

                var propStore1 = (IPropertyStore)link1;
                var pv1 = PropVariant.FromString("Adjust Strength & Warmth (Slider)");
                propStore1.SetValue(ref pkeyTitle, ref pv1);
                propStore1.Commit();
                collection.AddObject(link1);

                // Task 2: Toggle On / Off
                var link2 = (IShellLinkW)new ShellLinkClass();
                link2.SetPath(exePath);
                link2.SetArguments("--toggle");
                link2.SetDescription("Toggle Night Light on or off");
                link2.SetIconLocation(exePath, 0);

                var propStore2 = (IPropertyStore)link2;
                var pv2 = PropVariant.FromString("Toggle Night Light (On / Off)");
                propStore2.SetValue(ref pkeyTitle, ref pv2);
                propStore2.Commit();
                collection.AddObject(link2);

                // Task 3: Candle Preset
                var link3 = (IShellLinkW)new ShellLinkClass();
                link3.SetPath(exePath);
                link3.SetArguments("--preset 1900");
                link3.SetDescription("Set warmth to 1900K Candle");
                link3.SetIconLocation(exePath, 0);

                var propStore3 = (IPropertyStore)link3;
                var pv3 = PropVariant.FromString("Preset: Candle (1900K)");
                propStore3.SetValue(ref pkeyTitle, ref pv3);
                propStore3.Commit();
                collection.AddObject(link3);

                // Task 4: Night Owl Preset
                var link4 = (IShellLinkW)new ShellLinkClass();
                link4.SetPath(exePath);
                link4.SetArguments("--preset 2800");
                link4.SetDescription("Set warmth to 2800K Night Owl");
                link4.SetIconLocation(exePath, 0);

                var propStore4 = (IPropertyStore)link4;
                var pv4 = PropVariant.FromString("Preset: Night Owl (2800K)");
                propStore4.SetValue(ref pkeyTitle, ref pv4);
                propStore4.Commit();
                collection.AddObject(link4);

                // Task 5: Daylight Off Preset
                var link5 = (IShellLinkW)new ShellLinkClass();
                link5.SetPath(exePath);
                link5.SetArguments("--preset 6500");
                link5.SetDescription("Turn filter off (6500K Daylight)");
                link5.SetIconLocation(exePath, 0);

                var propStore5 = (IPropertyStore)link5;
                var pv5 = PropVariant.FromString("Preset: Daylight Off (6500K)");
                propStore5.SetValue(ref pkeyTitle, ref pv5);
                propStore5.Commit();
                collection.AddObject(link5);

                destList.AddUserTasks(collection);
                destList.CommitList();
                Console.WriteLine("SUCCESS: Taskbar JumpList registered!");
            }
            catch (Exception ex)
            {
                Console.WriteLine("ERROR: " + ex.Message);
            }
        }
    }
}
