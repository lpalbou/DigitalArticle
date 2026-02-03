# Files & data

## Uploads and the `data/` directory

Digital Article uses a per-article workspace. Generated code should read/write under `data/` unless you intentionally need another path.

Common patterns:

- Read CSV: `pd.read_csv('data/my_file.csv')`
- Save CSV: `df.to_csv('data/output.csv', index=False)`
- Save image: `fig.savefig('data/figure.png', dpi=200)`

## File previews

For large files, the system shows a **structured preview** (metadata + schema + samples) so the model can write correct code without sending the full file content.

This means:

- The preview helps code generation.
- The code that executes can still read the full file at runtime.

