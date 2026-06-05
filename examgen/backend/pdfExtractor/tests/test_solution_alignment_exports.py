from exam_parser.post import solution_alignment


def test_solution_alignment_exports_existing_helpers() -> None:
    assert hasattr(solution_alignment, "validate_solution_alignment")
    assert hasattr(solution_alignment, "validate_solution_extraction_result")
    assert not hasattr(solution_alignment, "align_solutions_to_questions")
