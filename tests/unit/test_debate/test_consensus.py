import pytest

from src.agents.schemas import Confidence, FindingDimension
from src.debate.consensus import aggregate_dimension_state, evaluate_finding_consensus, run_consensus_mapping
from src.debate.schemas import DebateArgument, DebatePersona, DebateStance, DimensionState
from src.debate.state_tracker import DimensionStateTracker


def create_mock_argument(
    persona: DebatePersona,
    stance: DebateStance,
    bm25_verified: bool,
    round_num: int = 1,
    finding_id: str = "f1",
    dimension: FindingDimension = FindingDimension.RISK_EXPOSURE
) -> DebateArgument:
    return DebateArgument(
        id=f"arg_{persona.value}_{round_num}",
        finding_id=finding_id,
        persona=persona,
        round=round_num,
        dimension=dimension,
        stance=stance,
        steelman="mock steelman",
        argument="mock argument",
        citations=[],
        confidence=Confidence.MEDIUM,
        contradiction_flag=False,
        bm25_verified=bm25_verified,
        dropout_flag=False,
        notes="",
    )


def test_evaluate_finding_consensus_settled():
    """Test that a finding is Settled when 4+ personas agree with BM25 evidence."""
    # 4 support (1 verified), 2 oppose (no verified)
    arguments = [
        create_mock_argument(DebatePersona.PROPONENT, DebateStance.SUPPORT, True),
        create_mock_argument(DebatePersona.CRITIC, DebateStance.SUPPORT, False),
        create_mock_argument(DebatePersona.DEVILS_ADVOCATE, DebateStance.SUPPORT, False),
        create_mock_argument(DebatePersona.INTEGRATION_REALIST, DebateStance.SUPPORT, False),
        create_mock_argument(DebatePersona.REGULATORS_EYE, DebateStance.OPPOSE, False),
        create_mock_argument(DebatePersona.VALUATION_SKEPTIC, DebateStance.OPPOSE, False),
    ]
    assert evaluate_finding_consensus(arguments) == DimensionState.SETTLED

    # 4 support but NO verified evidence -> Unresolved
    arguments_no_verif = [
        create_mock_argument(DebatePersona.PROPONENT, DebateStance.SUPPORT, False),
        create_mock_argument(DebatePersona.CRITIC, DebateStance.SUPPORT, False),
        create_mock_argument(DebatePersona.DEVILS_ADVOCATE, DebateStance.SUPPORT, False),
        create_mock_argument(DebatePersona.INTEGRATION_REALIST, DebateStance.SUPPORT, False),
        create_mock_argument(DebatePersona.REGULATORS_EYE, DebateStance.OPPOSE, False),
        create_mock_argument(DebatePersona.VALUATION_SKEPTIC, DebateStance.OPPOSE, False),
    ]
    assert evaluate_finding_consensus(arguments_no_verif) == DimensionState.UNRESOLVED


def test_evaluate_finding_consensus_contested():
    """Test that a finding is Contested when split with verified evidence on both sides."""
    arguments = [
        create_mock_argument(DebatePersona.PROPONENT, DebateStance.SUPPORT, True),
        create_mock_argument(DebatePersona.CRITIC, DebateStance.OPPOSE, True),
        create_mock_argument(DebatePersona.DEVILS_ADVOCATE, DebateStance.OPPOSE, False),
        create_mock_argument(DebatePersona.INTEGRATION_REALIST, DebateStance.SUPPORT, False),
        create_mock_argument(DebatePersona.REGULATORS_EYE, DebateStance.OPPOSE, False),
        create_mock_argument(DebatePersona.VALUATION_SKEPTIC, DebateStance.NEUTRAL, False),
    ]
    # Split stances with verified evidence -> CONTESTED
    assert evaluate_finding_consensus(arguments) == DimensionState.CONTESTED


def test_evaluate_finding_consensus_latest_round():
    """Test that the classifier uses the latest round for each persona."""
    # Round 1: Contested (Support has verified, Oppose has verified)
    arg_prop_r1 = create_mock_argument(DebatePersona.PROPONENT, DebateStance.SUPPORT, True, 1)
    arg_crit_r1 = create_mock_argument(DebatePersona.CRITIC, DebateStance.OPPOSE, True, 1)
    
    # Round 2: Critic changes mind to Support (still verified). Now we have 2 Support (both verified)
    # Let's say we have 4 support in round 2.
    arg_prop_r2 = create_mock_argument(DebatePersona.PROPONENT, DebateStance.SUPPORT, True, 2)
    arg_crit_r2 = create_mock_argument(DebatePersona.CRITIC, DebateStance.SUPPORT, True, 2)
    arg_da_r2 = create_mock_argument(DebatePersona.DEVILS_ADVOCATE, DebateStance.SUPPORT, False, 2)
    arg_ir_r2 = create_mock_argument(DebatePersona.INTEGRATION_REALIST, DebateStance.SUPPORT, False, 2)
    arg_re_r2 = create_mock_argument(DebatePersona.REGULATORS_EYE, DebateStance.NEUTRAL, False, 2)
    arg_vs_r2 = create_mock_argument(DebatePersona.VALUATION_SKEPTIC, DebateStance.NEUTRAL, False, 2)
    
    arguments = [
        arg_prop_r1, arg_crit_r1, 
        arg_prop_r2, arg_crit_r2, arg_da_r2, arg_ir_r2, arg_re_r2, arg_vs_r2
    ]
    
    # Because Critic's round 2 stance is Support, we have 4 Support (with verified evidence) -> SETTLED
    # If we incorrectly used all arguments, we might get CONTESTED because of arg_crit_r1.
    assert evaluate_finding_consensus(arguments) == DimensionState.SETTLED


def test_aggregate_dimension_state():
    """Test dimension rollup logic."""
    assert aggregate_dimension_state([DimensionState.SETTLED, DimensionState.SETTLED]) == DimensionState.SETTLED
    assert aggregate_dimension_state([DimensionState.SETTLED, DimensionState.CONTESTED]) == DimensionState.CONTESTED
    assert aggregate_dimension_state([DimensionState.SETTLED, DimensionState.UNRESOLVED]) == DimensionState.UNRESOLVED
    assert aggregate_dimension_state([DimensionState.CONTESTED, DimensionState.UNRESOLVED]) == DimensionState.CONTESTED


def test_run_consensus_mapping():
    """Test full consensus mapping workflow with the state tracker."""
    tracker = DimensionStateTracker(deal_id="test_deal")
    # Suppose 2 active dimensions: RISK_EXPOSURE, VALUATION_FAIRNESS
    tracker.initialize([FindingDimension.RISK_EXPOSURE, FindingDimension.VALUATION_FAIRNESS])
    
    # Finding 1 in RISK_EXPOSURE -> SETTLED (4+ agree)
    args_f1 = [
        create_mock_argument(DebatePersona.PROPONENT, DebateStance.SUPPORT, True, finding_id="f1", dimension=FindingDimension.RISK_EXPOSURE),
        create_mock_argument(DebatePersona.CRITIC, DebateStance.SUPPORT, False, finding_id="f1", dimension=FindingDimension.RISK_EXPOSURE),
        create_mock_argument(DebatePersona.DEVILS_ADVOCATE, DebateStance.SUPPORT, False, finding_id="f1", dimension=FindingDimension.RISK_EXPOSURE),
        create_mock_argument(DebatePersona.INTEGRATION_REALIST, DebateStance.SUPPORT, False, finding_id="f1", dimension=FindingDimension.RISK_EXPOSURE),
        create_mock_argument(DebatePersona.REGULATORS_EYE, DebateStance.OPPOSE, False, finding_id="f1", dimension=FindingDimension.RISK_EXPOSURE),
        create_mock_argument(DebatePersona.VALUATION_SKEPTIC, DebateStance.OPPOSE, False, finding_id="f1", dimension=FindingDimension.RISK_EXPOSURE),
    ]
    
    # Finding 2 in VALUATION_FAIRNESS -> CONTESTED (split with verified evidence)
    args_f2 = [
        create_mock_argument(DebatePersona.PROPONENT, DebateStance.SUPPORT, True, finding_id="f2", dimension=FindingDimension.VALUATION_FAIRNESS),
        create_mock_argument(DebatePersona.CRITIC, DebateStance.OPPOSE, True, finding_id="f2", dimension=FindingDimension.VALUATION_FAIRNESS),
        create_mock_argument(DebatePersona.DEVILS_ADVOCATE, DebateStance.SUPPORT, False, finding_id="f2", dimension=FindingDimension.VALUATION_FAIRNESS),
        create_mock_argument(DebatePersona.INTEGRATION_REALIST, DebateStance.OPPOSE, False, finding_id="f2", dimension=FindingDimension.VALUATION_FAIRNESS),
        create_mock_argument(DebatePersona.REGULATORS_EYE, DebateStance.NEUTRAL, False, finding_id="f2", dimension=FindingDimension.VALUATION_FAIRNESS),
        create_mock_argument(DebatePersona.VALUATION_SKEPTIC, DebateStance.NEUTRAL, False, finding_id="f2", dimension=FindingDimension.VALUATION_FAIRNESS),
    ]
    
    run_consensus_mapping(args_f1 + args_f2, tracker)
    
    # RISK_EXPOSURE has 1 finding which is SETTLED -> Dimension is SETTLED
    assert tracker.get_state(FindingDimension.RISK_EXPOSURE) == DimensionState.SETTLED
    
    # VALUATION_FAIRNESS has 1 finding which is CONTESTED -> Dimension is CONTESTED
    assert tracker.get_state(FindingDimension.VALUATION_FAIRNESS) == DimensionState.CONTESTED


def test_evaluate_finding_consensus_empty():
    assert evaluate_finding_consensus([]) == DimensionState.UNRESOLVED


def test_aggregate_dimension_state_empty():
    assert aggregate_dimension_state([]) == DimensionState.UNRESOLVED


def test_aggregate_dimension_state_mixed_unhandled():
    assert aggregate_dimension_state([DimensionState.SETTLED, DimensionState.ACTIVE]) == DimensionState.UNRESOLVED


def test_run_consensus_mapping_no_arguments():
    tracker = DimensionStateTracker(deal_id="test_deal")
    tracker.initialize([FindingDimension.RISK_EXPOSURE])
    
    run_consensus_mapping([], tracker)
    
    assert tracker.get_state(FindingDimension.RISK_EXPOSURE) == DimensionState.UNRESOLVED
