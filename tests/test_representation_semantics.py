"""Declared bitvector-model tests, not source extraction or real kernel runs."""
import copy
import itertools
import unittest

from linux_bug_analyze.representation_semantics import analyze_representation


def spec(width=32, storage="little", host="big", field="raw", operation="masked_nonzero",
         mask=1, mask_transform="host"):
    value = {"width": width, "storage_endian": storage, "host_endian": host,
             "field_transform": field, "operation": operation}
    if operation == "masked_nonzero":
        value.update(mask=mask, mask_transform=mask_transform)
    return value


def reference(configuration, value):
    """Independent byte serialization, not the implementation's bit mapping."""
    size = configuration["width"] // 8
    storage, host = configuration["storage_endian"], configuration["host_endian"]
    loaded = int.from_bytes(value.to_bytes(size, storage), host)
    field = (int.from_bytes(loaded.to_bytes(size, host), storage)
             if configuration["field_transform"] == "to_host" else loaded)
    operation = configuration["operation"]
    if operation == "masked_nonzero":
        mask = (int.from_bytes(configuration["mask"].to_bytes(size, storage), host)
                if configuration["mask_transform"] == "to_storage" else configuration["mask"])
        actual, expected = bool(field & mask), bool(value & configuration["mask"])
    else:
        mask = None
        actual = field == 0 if operation == "zero" else field != 0
        expected = value == 0 if operation == "zero" else value != 0
    return {"semantic_value": value, "storage_bytes_hex": value.to_bytes(size, storage).hex(),
            "loaded_value": loaded, "field_value": field,
            "mask_value": mask, "actual": actual, "expected": expected}


class RepresentationSemanticsTests(unittest.TestCase):
    def test_eight_bit_all_masks_and_full_unsigned_domain(self):
        for storage, host, field, mask_transform in itertools.product(
                ("little", "big"), ("little", "big"), ("raw", "to_host"), ("host", "to_storage")):
            for mask in range(256):
                configuration = spec(8, storage, host, field, mask=mask, mask_transform=mask_transform)
                result = analyze_representation(configuration)
                self.assertEqual(result["status"], "equivalent")
                self.assertEqual(result["proof_scope"]["domain_cardinality"], 256)
                for value in range(256):
                    observed = reference(configuration, value)
                    self.assertEqual(observed["actual"], observed["expected"])

    def test_wide_basis_and_byte_reference_agree_for_all_declared_transforms(self):
        for width, storage, host, field, mask_transform in itertools.product(
                (16, 32, 64), ("little", "big"), ("little", "big"), ("raw", "to_host"), ("host", "to_storage")):
            mask = 1 | (1 << (width - 2))
            configuration = spec(width, storage, host, field, mask=mask, mask_transform=mask_transform)
            result = analyze_representation(configuration)
            differences = []
            for row in result["basis"]["rows"]:
                value = 1 << row["semantic_bit"]
                independent = reference(configuration, value)
                self.assertEqual((row["actual"], row["expected"]), (independent["actual"], independent["expected"]))
                self.assertEqual(independent["loaded_value"], 1 << row["loaded_bit"])
                self.assertEqual(independent["field_value"], 1 << row["field_bit"])
                if independent["actual"] != independent["expected"]:
                    differences.append(row["semantic_bit"])
            self.assertEqual(result["basis"]["differing_bits"], differences)
            self.assertEqual(result["status"], "counterexample" if differences else "equivalent")
            self.assertEqual(result["sample"], reference(configuration, result["sample"]["semantic_value"]))

    def test_field_conversion_and_mask_conversion_are_individually_valid(self):
        for width in (16, 32, 64):
            for storage, host in (("little", "big"), ("big", "little")):
                for field, mask_transform in (("to_host", "host"), ("raw", "to_storage")):
                    result = analyze_representation(spec(width, storage, host, field, mask=0x41, mask_transform=mask_transform))
                    self.assertEqual(result["status"], "equivalent")
                    self.assertEqual(result["basis"]["actual_selected_bits"], result["basis"]["expected_selected_bits"])

    def test_raw_host_mask_gives_first_basis_counterexample(self):
        configuration = spec(mask=0x40)
        result = analyze_representation(configuration)
        self.assertEqual(result["status"], "counterexample")
        self.assertEqual(result["sample"], {"semantic_value": 0x40, "storage_bytes_hex": "40000000", "loaded_value": 0x40000000,
                                           "field_value": 0x40000000, "mask_value": 0x40,
                                           "actual": False, "expected": True})
        self.assertEqual(result["sample"]["semantic_value"], 1 << min(result["basis"]["differing_bits"]))

    def test_converting_both_operands_is_not_unconditionally_correct(self):
        configuration = spec(field="to_host", mask=0x40, mask_transform="to_storage")
        result = analyze_representation(configuration)
        self.assertEqual(result["status"], "counterexample")
        self.assertEqual(result["sample"], reference(configuration, result["sample"]["semantic_value"]))

    def test_zero_and_byte_symmetric_masks_are_equivalent(self):
        for width in (8, 16, 32, 64):
            symmetric = int.from_bytes(b"\x41" * (width // 8), "little")
            for mask in (0, symmetric, (1 << width) - 1):
                for field, mask_transform in itertools.product(("raw", "to_host"), ("host", "to_storage")):
                    result = analyze_representation(spec(width, field=field, mask=mask, mask_transform=mask_transform))
                    self.assertEqual(result["status"], "equivalent")

    def test_zero_and_nonzero_are_proved_by_bijection_not_just_sample(self):
        for width, storage, host, field, operation in itertools.product(
                (8, 16, 32, 64), ("little", "big"), ("little", "big"), ("raw", "to_host"), ("zero", "nonzero")):
            configuration = spec(width, storage, host, field, operation)
            result = analyze_representation(configuration)
            self.assertEqual(result["status"], "equivalent")
            self.assertTrue(result["basis"]["field_bit_mapping_is_bijection"])
            self.assertTrue(result["basis"]["zero_maps_to_zero"])
            self.assertIn("bijective_bit_permutation", result["basis"]["method"])
            self.assertEqual(result["sample"], reference(configuration, result["sample"]["semantic_value"]))
            for value in (0, 1, 1 << (width - 1), (1 << width) - 1):
                independent = reference(configuration, value)
                self.assertEqual(independent["actual"], independent["expected"])

    def test_asymmetric_mask_can_select_false_positive_basis(self):
        configuration = spec(mask=1 << 31)
        result = analyze_representation(configuration)
        self.assertEqual(result["status"], "counterexample")
        self.assertTrue(result["sample"]["actual"])
        self.assertFalse(result["sample"]["expected"])
        self.assertEqual(result["sample"], reference(configuration, result["sample"]["semantic_value"]))

    def test_bit_set_certificate_explains_full_domain_equivalence(self):
        result = analyze_representation(spec(field="raw", mask=0x2001, mask_transform="to_storage"))
        audit = result["basis"]
        self.assertEqual(result["status"], "equivalent")
        self.assertEqual(audit["actual_selected_bits"], [0, 13])
        self.assertEqual(audit["expected_selected_bits"], [0, 13])
        self.assertIn("every input", audit["proof_argument"])
        self.assertTrue(audit["basis_rows_are_not_a_random_test_sample"])
        self.assertIn("enclosing function or complete execution correctness", result["proof_scope"]["not_proved"])

    def test_strict_schema_and_invalid_semantics_fail_closed(self):
        invalid = [None, [], {}, {**spec(), "schema": "extra"}, {**spec(), "width": True},
                   {**spec(), "width": 32.0}, {**spec(), "width": 128}, {**spec(), "storage_endian": []},
                   {**spec(), "host_endian": "native"}, {**spec(), "field_transform": "guess"},
                   {**spec(), "operation": "greater_than"}, {**spec(), "operation": []},
                   {**spec(), "mask": True}, {**spec(), "mask": -1}, {**spec(), "mask": 1 << 32},
                   {**spec(), "mask": 1.0}, {**spec(), "mask_transform": "guess"},
                   {**spec(operation="zero"), "mask": 0}, {**spec(operation="nonzero"), "mask_transform": "host"}]
        missing_mask = spec()
        del missing_mask["mask"]
        invalid.append(missing_mask)
        for configuration in invalid:
            with self.subTest(configuration=configuration):
                result = analyze_representation(configuration)
                self.assertEqual(result["status"], "insufficient")
                self.assertIsNone(result["basis"])
                self.assertIsNone(result["sample"])
                self.assertIsNone(result["proof_scope"])
                self.assertTrue(result["reason"])

    def test_input_is_not_mutated_and_no_case_identity_is_accepted(self):
        configuration = spec()
        before = copy.deepcopy(configuration)
        analyze_representation(configuration)
        self.assertEqual(configuration, before)
        for key in ("function", "case", "architecture", "expected_status"):
            self.assertEqual(analyze_representation({**configuration, key: "unreviewed"})["status"], "insufficient")


if __name__ == "__main__":
    unittest.main()
