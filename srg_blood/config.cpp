class CfgPatches {
    class srg_blood {
        name = "SRG Blood";
        author = "STRATRECGRU";
        units[] = {};
        weapons[] = {};
        requiredVersion = 2.18;
        requiredAddons[] = {"cba_main", "ace_medical_blood"};
    };
};

class Extended_PreInit_EventHandlers {
    class srg_blood {
        init = "call compileScript ['\srg_blood\XEH_preInit.sqf']";
    };
};
