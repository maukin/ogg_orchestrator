from app.models.ogg_process_status import OGGProcessStatusRequest


class ExtractStatusRequestBuilder:
    def build(self, extract_name: str) -> OGGProcessStatusRequest:
        return OGGProcessStatusRequest(
            process_type="EXTRACT",
            process_name=extract_name,
            endpoint="/services/v2/extracts",
            artifact_prefix="ogg_rest_extract_status",
        )


class ReplicatStatusRequestBuilder:
    def build(self, replicat_name: str) -> OGGProcessStatusRequest:
        return OGGProcessStatusRequest(
            process_type="REPLICAT",
            process_name=replicat_name,
            endpoint="/services/v2/replicats",
            artifact_prefix="ogg_rest_replicat_status",
        )