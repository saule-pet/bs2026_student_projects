import pytest
import polars as pl
from lib.analysis.filters import apply_kinematic_filters


def dimuon_df(**overrides):
    """Build a minimal dimuon DataFrame. Row count is inferred from overrides."""
    n = len(next(iter(overrides.values()))) if overrides else 3
    base = {
        'Calculated_M': [3.0] * n,
        'pt1': [10.0] * n,
        'pt2': [10.0] * n,
        'eta1': [0.5] * n,
        'eta2': [0.5] * n,
    }
    base.update(overrides)
    return pl.DataFrame(base)


class TestMassRangeFilter:
    def test_keeps_events_inside_range(self):
        df = dimuon_df(Calculated_M=[2.5, 3.096, 4.9])
        result = apply_kinematic_filters(df, (2.0, 5.0), 0.0, 2.4, False)
        assert len(result) == 3

    def test_excludes_event_below_range(self):
        df = dimuon_df(Calculated_M=[1.0, 3.096, 4.0])
        result = apply_kinematic_filters(df, (2.0, 5.0), 0.0, 2.4, False)
        assert len(result) == 2
        assert 1.0 not in result['Calculated_M'].to_list()

    def test_excludes_event_above_range(self):
        df = dimuon_df(Calculated_M=[3.0, 5.1])
        result = apply_kinematic_filters(df, (2.0, 5.0), 0.0, 2.4, False)
        assert len(result) == 1
        assert result['Calculated_M'][0] == 3.0

    def test_boundary_values_are_inclusive(self):
        df = dimuon_df(Calculated_M=[2.0, 5.0])
        result = apply_kinematic_filters(df, (2.0, 5.0), 0.0, 2.4, False)
        assert len(result) == 2

    def test_empty_result_when_nothing_in_range(self):
        df = dimuon_df(Calculated_M=[0.5, 6.0])
        result = apply_kinematic_filters(df, (2.0, 5.0), 0.0, 2.4, False)
        assert len(result) == 0


class TestPtFilter:
    def test_excludes_event_where_pt1_too_low(self):
        df = dimuon_df(pt1=[10.0, 4.0], pt2=[10.0, 10.0],
                       Calculated_M=[3.0, 3.0], eta1=[0.5, 0.5], eta2=[0.5, 0.5])
        result = apply_kinematic_filters(df, (2.0, 5.0), 5.0, 2.4, False)
        assert len(result) == 1

    def test_excludes_event_where_pt2_too_low(self):
        df = dimuon_df(pt1=[10.0, 10.0], pt2=[10.0, 4.0],
                       Calculated_M=[3.0, 3.0], eta1=[0.5, 0.5], eta2=[0.5, 0.5])
        result = apply_kinematic_filters(df, (2.0, 5.0), 5.0, 2.4, False)
        assert len(result) == 1

    def test_zero_pt_min_keeps_all(self):
        df = dimuon_df(pt1=[0.1, 0.1], pt2=[0.1, 0.1],
                       Calculated_M=[3.0, 3.0], eta1=[0.5, 0.5], eta2=[0.5, 0.5])
        result = apply_kinematic_filters(df, (2.0, 5.0), 0.0, 2.4, False)
        assert len(result) == 2


class TestEtaFilter:
    def test_excludes_event_with_high_eta1(self):
        df = dimuon_df(eta1=[0.5, 2.5], eta2=[0.5, 0.5],
                       Calculated_M=[3.0, 3.0])
        result = apply_kinematic_filters(df, (2.0, 5.0), 0.0, 2.4, False)
        assert len(result) == 1

    def test_excludes_event_with_high_eta2(self):
        df = dimuon_df(eta1=[0.5, 0.5], eta2=[0.5, -2.5],
                       Calculated_M=[3.0, 3.0])
        result = apply_kinematic_filters(df, (2.0, 5.0), 0.0, 2.4, False)
        assert len(result) == 1

    def test_negative_eta_uses_absolute_value(self):
        df = dimuon_df(eta1=[-2.5, 0.0], eta2=[0.0, 0.0],
                       Calculated_M=[3.0, 3.0])
        result = apply_kinematic_filters(df, (2.0, 5.0), 0.0, 2.4, False)
        assert len(result) == 1
        assert result['eta1'][0] == 0.0

    def test_eta_boundary_is_inclusive(self):
        df = dimuon_df(eta1=[2.4], eta2=[2.4], Calculated_M=[3.0])
        result = apply_kinematic_filters(df, (2.0, 5.0), 0.0, 2.4, False)
        assert len(result) == 1


class TestOppositeChargeFilter:
    def _charge_df(self, q1_vals, q2_vals):
        n = len(q1_vals)
        return pl.DataFrame({
            'Calculated_M': [3.0] * n,
            'pt1': [10.0] * n, 'pt2': [10.0] * n,
            'eta1': [0.5] * n, 'eta2': [0.5] * n,
            'Q1': q1_vals, 'Q2': q2_vals,
        })

    def test_keeps_only_opposite_charge_pairs(self):
        df = self._charge_df([1, 1, -1], [-1, 1, -1])
        result = apply_kinematic_filters(df, (2.0, 5.0), 0.0, 2.4, True)
        assert len(result) == 1
        assert result['Q1'][0] == 1
        assert result['Q2'][0] == -1

    def test_disabled_keeps_same_charge_pairs(self):
        df = self._charge_df([1, 1], [1, -1])
        result = apply_kinematic_filters(df, (2.0, 5.0), 0.0, 2.4, False)
        assert len(result) == 2

    def test_skipped_when_charge_columns_absent(self):
        df = dimuon_df()
        result = apply_kinematic_filters(df, (2.0, 5.0), 0.0, 2.4, True)
        assert len(result) == 3


class TestSingleParticleBranch:
    def _single_df(self, masses, pts, etas):
        return pl.DataFrame({
            'Calculated_M': masses,
            'pt': pts,
            'eta': etas,
        })

    def test_single_particle_mass_filter(self):
        df = self._single_df([80.0, 50.0, 80.0], [30.0, 30.0, 30.0], [0.5, 0.5, 0.5])
        result = apply_kinematic_filters(df, (70.0, 110.0), 0.0, 2.4, False)
        assert len(result) == 2

    def test_single_particle_pt_filter(self):
        df = self._single_df([80.0, 80.0], [30.0, 5.0], [0.5, 0.5])
        result = apply_kinematic_filters(df, (70.0, 110.0), 10.0, 2.4, False)
        assert len(result) == 1

    def test_single_particle_eta_filter(self):
        df = self._single_df([80.0, 80.0], [30.0, 30.0], [0.5, 3.0])
        result = apply_kinematic_filters(df, (70.0, 110.0), 0.0, 2.4, False)
        assert len(result) == 1
