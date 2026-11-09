# srg_ace_blood

Replaces the ACE3 medical blood drop visuals with four darker, more natural blood variants, one for each ACE drop size.

Visual only. ACE still handles all spawning, rates, cleanup, and the "Blood Drops" setting. The mod runs one preInit handler that points ACE's drop model table at these models. It adds no per-frame handlers and no scheduled scripts.

This is not an official ACE3 release and is not affiliated with the ACE3 team.

## Requirements

- [CBA_A3](https://github.com/CBATeam/CBA_A3)
- [ACE3](https://github.com/acemod/ACE3) (medical)

The mod is required on every client. Blood drops are global objects, so a client without it sees missing-model errors.

## Variants

| ACE slot | Size | ACE uses it for |
|---|---|---|
| `blooddrop_1` | 0.23 m | Trail behind each hit (up to 3), lightest bleeding |
| `blooddrop_2` | 0.35 m | First drop of every hit |
| `blooddrop_3` | 0.40 m | Moderate bleeding |
| `blooddrop_4` | 0.49 m | Heavy bleeding |

Each variant has its own model, color texture, thermal texture, and material.

## Repository layout

```
srg_blood/                 addon folder, pack this as the PBO
  config.cpp               CfgPatches, preInit hook
  XEH_preInit.sqf          writes the SRG models into ace_medical_blood_models
  data/
    srg_drop_1..4.p3d      drop models (MLOD)
    srg_blood_1..4.rvmat   materials
    srg_blood_1..4_ca.paa      color textures, 256x256 DXT5
    srg_blood_1..4_ti_ca.paa   thermal textures, 128x128 DXT5
    srg_blood_smdi.paa     specular, shared
    model.cfg
source/textures/           editable PNG sources for the PAA textures
```

## Building

Pack `srg_blood/` as `srg_blood.pbo`. The PBO must be named `srg_blood` with no prefix, since script and asset paths are written as `\srg_blood\...`.

To change a texture, edit the PNG in `source/textures/`, convert it to PAA with the same name, and replace the file in `srg_blood/data/`.

## Compatibility

Works with anything that uses ACE3's own blood drop spawning, including ACE medical extensions that leave it unchanged. It conflicts only with mods that replace ACE's blood drop spawning or write to `ace_medical_blood_models`.

If a future ACE update renames or restructures `ace_medical_blood_models`, the mod leaves ACE's default drops in place and logs this to the RPT:

```
[srg_blood] ace_medical_blood_models not defined, ACE medical_blood missing or changed. Skipping.
```

## License

GPLv2, see [LICENSE](LICENSE). The drop models, materials, and specular texture are derived from [ACE3](https://github.com/acemod/ACE3) (GPLv2).
