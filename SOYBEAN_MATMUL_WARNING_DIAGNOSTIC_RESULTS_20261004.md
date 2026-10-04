# Soybean matmul warning numerical diagnostic

## Conclusion

The disclosed NumPy `matmul` warnings are reproducible on the synthetic
distribution-family orchestration design, but they do not correspond to a
material numerical discrepancy in this test. Warning-producing products are
finite and agree with non-BLAS `einsum`, 50-digit Decimal Gram accumulation,
independent least squares, and an independently reconstructed CR2 covariance.

This is a bounded environment-specific classification, not a production-fit
result or a general waiver of numerical checks. The diagnosed environment is
macOS ARM64, Python 3.12.14, NumPy 2.2.6, and Apple's Accelerate BLAS/LAPACK.
No real outcome was read, no production token was created, the frozen engine
was not changed, and all promotion gates remain closed.

## Reproduction

The diagnostic recreated the exact synthetic distribution design used by the
orchestration test: 2,100 levels, 2,040 consecutive pairs, 60 cells, 34
pair-end years, 12 full-rank columns, and 30 ten-degree spatial clusters.

Captured warning counts were:

- direct `X'X` matmul: 3;
- full engine fit: 279;
- bread-root matmul: 3; and
- cluster matmul products: 180.

Each warning location reported the same three labels: divide by zero,
overflow, and invalid value encountered in `matmul`. The non-BLAS `einsum`
Gram and NumPy `longdouble` `einsum` Gram emitted zero warnings. On this
platform NumPy reports `longdouble_bits=64`, so `longdouble` is not extended
precision; the independent 50-digit Decimal accumulation is the actual
higher-precision Gram reference.

## Numerical comparisons

All design, outcome, Gram, coefficient, covariance, standard-error,
degrees-of-freedom, p-value, and confidence-interval arrays were finite.
Maximum relative discrepancies were:

- matmul Gram versus `einsum`: `0.0`;
- `einsum` Gram versus 50-digit Decimal: `1.5938106100287927e-15`;
- matmul versus `einsum` bread root, cluster products, and cluster Grams:
  `0.0` each;
- engine coefficient versus `numpy.linalg.lstsq`:
  `1.942890293094024e-16`;
- engine CR2 covariance versus independent `einsum` reconstruction:
  `2.710505431213761e-20`; and
- engine standard errors versus the independent covariance:
  `1.734723475976807e-18`.

The design condition number was `154.8544457447439`, the Gram condition
number was `23979.899366911824`, and the maximum cluster hat eigenvalue was
`0.08743020742937267`. Thus the synthetic warning does not coincide with
rank failure, extreme cluster leverage, nonfinite output, or disagreement
between independent numerical routes.

## Resource and provenance boundary

The diagnostic peaked at 174,882,816 bytes (166.78 MiB), below the
536,870,912-byte cap. The independent validator peaked at 23,314,432 bytes
(22.23 MiB) and recomputed every tolerance gate from the receipt.

Bound artifacts and SHA-256 hashes:

- `scripts/diagnose_soybean_orchestrator_matmul_warnings.py`:
  `9c120e7e7f7ab4a5cb4b880ff2d25aebc2da296dc452c458ce77420f1a07fd05`
- `config/soybean_pooled_response_matmul_diagnostic_v1.toml`:
  `8c20ce23f26aac8ab9706f1bb1003f169440230f30696edf5036bfddf5f00bc8`
- `scripts/validate_soybean_matmul_numerical_diagnostic.py`:
  `2e6e78c23af1169b9bb3b6a683d4276709a3eca23420a7838e8948fea02c4dfd`
- diagnostic receipt:
  `f7641952136a17b5eab4d4a91308ca2e1d3ef5d4d59f016466ee417a50ae9b5c`
- validation receipt:
  `f0203eeead84b7597953c9ea4f7a7e8908ff924a8fbdc205d52caef169a2d58d`
- unchanged pooled engine:
  `a437fab438e17fccdc6bf9780de6799e5d11306174f18c55e2bd286f494f0b66`

## Gate interpretation

For this synthetic design, the evidence supports treating the messages as
environment/Accelerate warning-flag behavior rather than evidence of a bad
matrix product. This does not authorize production access or fitting. A future
authorized execution must still satisfy the engine's rank and finite-value
guards, the 512 MiB limit, redaction, and the separate terminal-validation
gate.
