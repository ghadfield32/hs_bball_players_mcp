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
from .maxpreps import MaxPrepsDataSource
from .mn_hub import MNHubDataSource
from .psal import PSALDataSource
from .wsn import WSNDataSource

# State associations - Southeast
from .alabama_ahsaa import AlabamaAhsaaDataSource
from .arkansas_aaa import ArkansasAaaDataSource
from .georgia_ghsa import GeorgiaGhsaDataSource
from .kentucky_khsaa import KentuckyKhsaaDataSource
from .louisiana_lhsaa import LouisianaLhsaaDataSource
from .mississippi_mhsaa import MississippiMhsaaDataSource
from .nchsaa import NCHSAADataSource
from .south_carolina_schsl import SouthCarolinaSchslDataSource
from .tennessee_tssaa import TennesseeTssaaDataSource
from .virginia_vhsl import VirginiaVhslDataSource
from .west_virginia_wvssac import WestVirginiaWvssacDataSource

# State associations - Northeast
from .connecticut_ciac import ConnecticutCiacDataSource
from .delaware_diaa import DelawareDiaaDataSource
from .maine_mpa import MaineMpaDataSource
from .maryland_mpssaa import MarylandMpssaaDataSource
from .massachusetts_miaa import MassachusettsMiaaDataSource
from .nepsac import NEPSACDataSource
from .new_hampshire_nhiaa import NewHampshireNhiaaDataSource
from .new_jersey_njsiaa import NewJerseyNjsiaaDataSource
from .pennsylvania_piaa import PennsylvaniaPiaaDataSource
from .rhode_island_riil import RhodeIslandRiilDataSource
from .vermont_vpa import VermontVpaDataSource

# State associations - Midwest
from .indiana_ihsaa import IndianaIhsaaDataSource
from .kansas_kshsaa import KansasKshsaaDataSource
from .michigan_mhsaa import MichiganMhsaaDataSource
from .missouri_mshsaa import MissouriMshsaaDataSource
from .nebraska_nsaa import NebraskaNsaaDataSource
from .north_dakota_ndhsaa import NorthDakotaNdhsaaDataSource
from .ohio_ohsaa import OhioOhsaaDataSource

# State associations - Southwest/West
from .alaska_asaa import AlaskaAsaaDataSource
from .colorado_chsaa import ColoradoChsaaDataSource
from .dc_dciaa import DcDciaaDataSource
from .montana_mhsa import MontanaMhsaDataSource
from .new_mexico_nmaa import NewMexicoNmaaDataSource
from .oklahoma_ossaa import OklahomaOssaaDataSource
from .utah_uhsaa import UtahUhsaaDataSource
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
    "MaxPrepsDataSource",
    "MNHubDataSource",
    "PSALDataSource",
    "WSNDataSource",
    "AlabamaAhsaaDataSource",
    "ArkansasAaaDataSource",
    "GeorgiaGhsaDataSource",
    "KentuckyKhsaaDataSource",
    "LouisianaLhsaaDataSource",
    "MississippiMhsaaDataSource",
    "NCHSAADataSource",
    "SouthCarolinaSchslDataSource",
    "TennesseeTssaaDataSource",
    "VirginiaVhslDataSource",
    "WestVirginiaWvssacDataSource",
    "ConnecticutCiacDataSource",
    "DelawareDiaaDataSource",
    "MaineMpaDataSource",
    "MarylandMpssaaDataSource",
    "MassachusettsMiaaDataSource",
    "NEPSACDataSource",
    "NewHampshireNhiaaDataSource",
    "NewJerseyNjsiaaDataSource",
    "PennsylvaniaPiaaDataSource",
    "RhodeIslandRiilDataSource",
    "VermontVpaDataSource",
    "IndianaIhsaaDataSource",
    "KansasKshsaaDataSource",
    "MichiganMhsaaDataSource",
    "MissouriMshsaaDataSource",
    "NebraskaNsaaDataSource",
    "NorthDakotaNdhsaaDataSource",
    "OhioOhsaaDataSource",
    "AlaskaAsaaDataSource",
    "ColoradoChsaaDataSource",
    "DcDciaaDataSource",
    "MontanaMhsaDataSource",
    "NewMexicoNmaaDataSource",
    "OklahomaOssaaDataSource",
    "UtahUhsaaDataSource",
    "WyomingWhsaaDataSource",
]
