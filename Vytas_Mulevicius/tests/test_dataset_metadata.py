import pytest
from lib.analysis.dataset_metadata import get_metadata, build_file_options, KNOWN_METADATA


class TestGetMetadata:
    def test_known_file_jpsi(self):
        mn, mx, mass, name = get_metadata("Jpsimumu_Run2011A.csv")
        assert mn == 2.0
        assert mx == 5.0
        assert mass == 3.096
        assert name == "J/ψ"

    def test_known_file_zmumu(self):
        mn, mx, mass, name = get_metadata("Zmumu_Run2011A.csv")
        assert mn == 70.0
        assert mx == 110.0
        assert mass == 91.1876
        assert name == "Z"

    def test_known_file_upsilon(self):
        _, _, mass, name = get_metadata("Ymumu_Run2011A.csv")
        assert mass == 9.460
        assert name == "Υ"

    def test_known_file_w_boson(self):
        _, _, mass, name = get_metadata("Wenu.csv")
        assert mass == 80.38
        assert name == "W"

    def test_strips_directory_path(self):
        _, _, _, name = get_metadata("data/Jpsimumu_Run2011A.csv")
        assert name == "J/ψ"

    def test_strips_url_query_string(self):
        _, _, _, name = get_metadata("Jpsimumu_Run2011A.csv?token=abc123")
        assert name == "J/ψ"

    def test_strips_path_and_query_combined(self):
        _, _, _, name = get_metadata("root://server//eos/Jpsimumu_Run2011A.csv?timeout=10")
        assert name == "J/ψ"

    def test_unknown_csv_returns_fallback_defaults(self):
        mn, mx, mass, name = get_metadata("MyParticle_Run2015.csv")
        assert mn == 0.0
        assert mx == 120.0
        assert mass == 0.0
        assert name == "MyParticle"

    def test_unknown_root_extracts_particle_name(self):
        # function splits on '_' and takes the first part
        _, _, _, name = get_metadata("custom_data.root")
        assert name == "custom"

    def test_unknown_file_no_underscore(self):
        _, _, _, name = get_metadata("events.csv")
        assert name == "events"

    def test_all_known_files_covered(self):
        for fname in KNOWN_METADATA:
            mn, mx, mass, name = get_metadata(fname)
            assert mass > 0
            assert mx > mn


class TestBuildFileOptions:
    def test_known_file_gets_display_label(self):
        opts, file_map = build_file_options(["Jpsimumu_Run2011A.csv"])
        assert opts[0] == "J/ψ → μμ (2011A)"
        assert file_map["J/ψ → μμ (2011A)"] == "Jpsimumu_Run2011A.csv"

    def test_unknown_file_gets_custom_label(self):
        opts, file_map = build_file_options(["custom_data.csv"])
        assert opts[0] == "📦 Custom: custom_data.csv"
        assert file_map["📦 Custom: custom_data.csv"] == "custom_data.csv"

    def test_mixed_known_and_unknown(self):
        opts, file_map = build_file_options(["Zmumu_Run2011A.csv", "custom.root"])
        assert len(opts) == 2
        assert "Z → μμ (2011A)" in opts
        assert "📦 Custom: custom.root" in opts

    def test_empty_input(self):
        opts, file_map = build_file_options([])
        assert opts == []
        assert file_map == {}

    def test_preserves_input_order(self):
        files = ["Zmumu_Run2011A.csv", "Jpsimumu_Run2011A.csv", "Ymumu_Run2011A.csv"]
        opts, _ = build_file_options(files)
        assert opts[0] == "Z → μμ (2011A)"
        assert opts[1] == "J/ψ → μμ (2011A)"
        assert opts[2] == "Υ → μμ (2011A)"

    def test_file_map_is_invertible(self):
        files = ["Zmumu_Run2011A.csv", "Wenu.csv"]
        opts, file_map = build_file_options(files)
        for label in opts:
            assert file_map[label] in files
