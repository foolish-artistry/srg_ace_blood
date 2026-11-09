class CfgPatches {
    class srg_ace_blood {
        name = "SRG ACE Blood";
        author = "STRATRECGRU";
        units[] = {};
        weapons[] = {};
        requiredVersion = 2.18;
        requiredAddons[] = {"cba_main", "ace_medical_blood"};
    };
};

class Extended_PreInit_EventHandlers {
    class srg_ace_blood {
        init = "call compileScript ['\srg_ace_blood\XEH_preInit.sqf']";
    };
};
