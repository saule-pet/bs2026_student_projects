import io
import pytest
import pandas as pd
from lib.analysis.plot_mass import generate_publication_plot


PNG_HEADER = b'\x89PNG\r\n\x1a\n'


def jpsi_df():
    """Minimal J/ψ-like DataFrame with mass values in range."""
    return pd.DataFrame({'Calculated_M': [3.0, 3.05, 3.096, 3.15, 3.2]})


class TestReturnType:
    def test_returns_bytes_io(self):
        result = generate_publication_plot(jpsi_df())
        assert isinstance(result, io.BytesIO)

    def test_buffer_starts_with_png_header(self):
        result = generate_publication_plot(jpsi_df())
        assert result.read(8) == PNG_HEADER

    def test_buffer_is_seeked_to_start(self):
        result = generate_publication_plot(jpsi_df())
        assert result.tell() == 0

    def test_buffer_is_non_empty(self):
        result = generate_publication_plot(jpsi_df())
        assert len(result.read()) > 0


class TestColumnFallback:
    def test_prefers_calculated_m_over_m(self):
        df = pd.DataFrame({
            'Calculated_M': [3.0, 3.1, 3.2],
            'M': [99.0, 99.0, 99.0],
        })
        result = generate_publication_plot(df)
        assert isinstance(result, io.BytesIO)

    def test_falls_back_to_m_when_no_calculated_m(self):
        df = pd.DataFrame({'M': [91.0, 91.2, 90.8]})
        result = generate_publication_plot(df, mass_range=(70.0, 110.0))
        assert isinstance(result, io.BytesIO)

    def test_raises_value_error_when_no_mass_column(self):
        df = pd.DataFrame({'pt': [10.0, 20.0], 'eta': [0.5, 1.0]})
        with pytest.raises(ValueError, match="Calculated_M"):
            generate_publication_plot(df)


class TestParameters:
    def test_custom_particle_name(self):
        result = generate_publication_plot(jpsi_df(), particle_name="Z")
        assert isinstance(result, io.BytesIO)

    def test_custom_expected_mass(self):
        result = generate_publication_plot(jpsi_df(), expected_mass=3.5)
        assert isinstance(result, io.BytesIO)

    def test_custom_mass_range(self):
        result = generate_publication_plot(jpsi_df(), mass_range=(2.5, 4.0))
        assert isinstance(result, io.BytesIO)

    def test_z_boson_parameters(self):
        df = pd.DataFrame({'Calculated_M': [90.0, 91.0, 91.2, 92.0, 93.0]})
        result = generate_publication_plot(
            df,
            particle_name="Z",
            expected_mass=91.1876,
            mass_range=(70.0, 110.0),
        )
        assert result.read(8) == PNG_HEADER

    def test_each_call_produces_independent_buffer(self):
        r1 = generate_publication_plot(jpsi_df())
        r2 = generate_publication_plot(jpsi_df())
        assert r1 is not r2
        assert r1.read() == r2.read()
