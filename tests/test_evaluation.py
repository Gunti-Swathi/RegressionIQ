from regressioniq.evaluation.runner import run_evaluation


def test_phase_one_eval_dataset_passes():
    metrics = run_evaluation("eval_cases")

    assert metrics["cases"] >= 6
    assert metrics["classification_accuracy"] == 100.0
    assert metrics["test_trigger_accuracy"] == 100.0
    assert metrics["changed_function_accuracy"] == 100.0

