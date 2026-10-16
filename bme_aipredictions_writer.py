"""Writer for Bosch ``.aipredictions`` files."""

import json
from pathlib import Path
from typing import Any, Dict

from bme_ai_predictions import AIPredictions

_PLACEHOLDER = "@@BME_AI_DATA_BLOCK@@"


class AIPredictionsWriter:
    """Serialize AI config, run header and prediction rows as one JSON file."""

    def write(
        self,
        ai_config: Dict[str, Any],
        raw_data_header: Dict[str, Any],
        bsec_version: str,
        predictions: AIPredictions,
        output_path: str,
    ) -> str:
        header = {}
        for key, value in raw_data_header.items():
            header[key] = value
            if key == "firmwareVersion":
                header["bsecVersion"] = bsec_version
        header.setdefault("bsecVersion", bsec_version)

        document = {
            "aiConfigHeader": ai_config["aiConfigHeader"],
            "aiConfigBody": ai_config["aiConfigBody"],
            "aiPredictionsDataHeader": header,
            "aiPredictionsDataBody": {
                "dataColumns": predictions.columns,
                "dataBlock": _PLACEHOLDER,
            },
        }
        text = json.dumps(document, indent="\t")
        rows = ",\n\t\t\t".join(
            json.dumps(row, separators=(",", ":")) for row in predictions.rows
        )
        text = text.replace(
            json.dumps(_PLACEHOLDER), "[\n\t\t\t" + rows + "\n\t\t]"
        )

        path = Path(output_path)
        path.write_text(text + "\n", encoding="utf-8")
        return str(path)
