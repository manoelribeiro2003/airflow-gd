MERGE INTO [dbengenharia].[dbo].[fSegmentacao_Simon] AS TARGET
USING (SELECT
            :data as data ,
            :equipamento equipamento,
            :segmentacao as segmentacao,
            :updated_at as updated_at) AS SOURCE
ON target.equipamento = source.equipamento AND target.data = source.data
WHEN MATCHED THEN
    UPDATE SET
        target.segmentacao = source.segmentacao,
        target.updated_at = source.updated_at
WHEN NOT MATCHED THEN
    INSERT (data, equipamento, segmentacao, updated_at)
    VALUES(source.data, source.equipamento, source.segmentacao, source.updated_at);
