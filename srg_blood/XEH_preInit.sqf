/*
 * srg_blood
 * Points ACE3 medical_blood at SRG drop models.
 * ACE builds ace_medical_blood_models (hashmap) in its own preInit;
 * requiredAddons ace_medical_blood makes this run after it.
 * Higher number = bigger drop, same as ACE.
 */

if (isNil "ace_medical_blood_models") exitWith {
    diag_log text "[srg_blood] ace_medical_blood_models not defined, ACE medical_blood missing or changed. Skipping.";
};

{
    ace_medical_blood_models set _x;
} forEach [
    ["blooddrop_1", "\srg_blood\data\srg_drop_1.p3d"],
    ["blooddrop_2", "\srg_blood\data\srg_drop_2.p3d"],
    ["blooddrop_3", "\srg_blood\data\srg_drop_3.p3d"],
    ["blooddrop_4", "\srg_blood\data\srg_drop_4.p3d"]
];

diag_log text "[srg_blood] blood drop models replaced";
