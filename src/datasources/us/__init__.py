"""US DataSource Adapters."""

# National circuits
from .bound import BoundDataSource
from .eybl import EYBLDataSource
from .eybl_girls import EYBLGirlsDataSource
from .grind_session import GrindSessionDataSource
from .ote import OTEDataSource
from .rankone import RankOneDataSource
from .sblive import SBLiveDataSource
from .three_ssb import ThreeSSBDataSource
from .three_ssb_girls import ThreeSSBGirlsDataSource
from .uaa import UAADataSource
from .uaa_girls import UAAGirlsDataSource

# Regional/State platforms
from .fhsaa import FHSAADataSource
from .hhsaa import HHSAADataSource
from .mn_hub import MNHubDataSource
from .psal import PSALDataSource
from .wsn import WSNDataSource

# Phase 17 - High-Impact State Associations
from .california_cif_ss import CaliforniaCIFSSDataSource
from .texas_uil import TexasUILDataSource
from .florida_fhsaa import FloridaFHSAADataSource
from .georgia_ghsa import GeorgiaGHSADataSource

# State associations - Southeast
from .alabama_ahsaa import AlabamaAHSAADataSource
from .arkansas_aaa import ArkansasAAADataSource
from .kentucky_khsaa import KentuckyKHSAADataSource
from .louisiana_lhsaa import LouisianaLHSAADataSource
from .mississippi_mhsaa_ms import MississippiMHSAA_MSDataSource
from .nchsaa import NCHSAADataSource
from .south_carolina_schsl import SouthCarolinaSCHSLDataSource
from .tennessee_tssaa import TennesseeTSSAADataSource
from .virginia_vhsl import VirginiaVHSLDataSource
from .west_virginia_wvssac import WestVirginiaWvssacDataSource

# State associations - Northeast
from .connecticut_ciac import ConnecticutCIACDataSource
from .delaware_diaa import DelawareDiaaDataSource
from .maine_mpa import MaineMpaDataSource
from .maryland_mpssaa import MarylandMPSSAADataSource
from .massachusetts_miaa import MassachusettsMiaaDataSource
from .nepsac import NEPSACDataSource
from .new_hampshire_nhiaa import NewHampshireNhiaaDataSource
from .new_jersey_njsiaa import NewJerseyNJSIAADataSource
from .newyork_nysphsaa import NewYorkNYSPHSAADataSource
from .pennsylvania_piaa import PennsylvaniaPIAADataSource
from .rhode_island_riil import RhodeIslandRiilDataSource
from .vermont_vpa import VermontVpaDataSource

# State associations - Midwest
from .illinois_ihsa import IllinoisIHSADataSource as IHSADataSource
from .indiana_ihsaa import IndianaIHSAADataSource
from .iowa_ihsaa import IowaIHSAADataSource
from .kansas_kshsaa import KansasKSHSAADataSource
from .michigan_mhsaa import MichiganMHSAADataSource
from .minnesota_mshsl import MinnesotaMSHSLDataSource
from .missouri_mshsaa import MissouriMSHSAADataSource
from .nebraska_nsaa import NebraskaNSAADataSource
from .north_dakota_ndhsaa import NorthDakotaNdhsaaDataSource
from .ohio_ohsaa import OhioOHSAADataSource
from .south_dakota_sdhsaa import SouthDakotaSDHSAADataSource
from .wisconsin_wiaa import WisconsinWIAADataSource
from .wisconsin_maxpreps import MaxPrepsWisconsinDataSource

# State associations - Southwest/West
from .alaska_asaa import AlaskaAsaaDataSource
from .arizona_aia import ArizonaAIADataSource
from .colorado_chsaa import ColoradoCHSAADataSource
from .dc_dciaa import DcDciaaDataSource
from .idaho_ihsaa import IdahoIHSAADataSource
from .montana_mhsa import MontanaMhsaDataSource
from .nevada_niaa import NevadaNIAADataSource
from .new_mexico_nmaa import NewMexicoNmaaDataSource
from .oklahoma_ossaa import OklahomaOssaaDataSource
from .oregon_osaa import OregonOSAADataSource
from .utah_uhsaa import UtahUHSAADataSource
from .washington_wiaa import WashingtonWIAADataSource
from .wyoming_whsaa import WyomingWhsaaDataSource

__all__ = [
    "BoundDataSource",
    "EYBLDataSource",
    "EYBLGirlsDataSource",
    "GrindSessionDataSource",
    "OTEDataSource",
    "RankOneDataSource",
    "SBLiveDataSource",
    "ThreeSSBDataSource",
    "ThreeSSBGirlsDataSource",
    "UAADataSource",
    "UAAGirlsDataSource",
    "FHSAADataSource",
    "HHSAADataSource",
    "MNHubDataSource",
    "PSALDataSource",
    "WSNDataSource",
    "CaliforniaCIFSSDataSource",
    "TexasUILDataSource",
    "FloridaFHSAADataSource",
    "GeorgiaGHSADataSource",
    "AlabamaAHSAADataSource",
    "ArkansasAAADataSource",
    "KentuckyKHSAADataSource",
    "LouisianaLHSAADataSource",
    "MississippiMHSAA_MSDataSource",
    "NCHSAADataSource",
    "SouthCarolinaSCHSLDataSource",
    "TennesseeTSSAADataSource",
    "VirginiaVHSLDataSource",
    "WestVirginiaWvssacDataSource",
    "ConnecticutCIACDataSource",
    "DelawareDiaaDataSource",
    "MaineMpaDataSource",
    "MarylandMPSSAADataSource",
    "MassachusettsMiaaDataSource",
    "NEPSACDataSource",
    "NewHampshireNhiaaDataSource",
    "NewJerseyNJSIAADataSource",
    "NewYorkNYSPHSAADataSource",
    "PennsylvaniaPIAADataSource",
    "RhodeIslandRiilDataSource",
    "VermontVpaDataSource",
    "IHSADataSource",
    "IndianaIHSAADataSource",
    "IowaIHSAADataSource",
    "KansasKSHSAADataSource",
    "MichiganMHSAADataSource",
    "MinnesotaMSHSLDataSource",
    "MissouriMSHSAADataSource",
    "NebraskaNSAADataSource",
    "NorthDakotaNdhsaaDataSource",
    "OhioOHSAADataSource",
    "SouthDakotaSDHSAADataSource",
    "WisconsinWIAADataSource",
    "MaxPrepsWisconsinDataSource",
    "AlaskaAsaaDataSource",
    "ArizonaAIADataSource",
    "ColoradoCHSAADataSource",
    "DcDciaaDataSource",
    "IdahoIHSAADataSource",
    "MontanaMhsaDataSource",
    "NevadaNIAADataSource",
    "NewMexicoNmaaDataSource",
    "OklahomaOssaaDataSource",
    "OregonOSAADataSource",
    "UtahUHSAADataSource",
    "WashingtonWIAADataSource",
    "WyomingWhsaaDataSource",
]
