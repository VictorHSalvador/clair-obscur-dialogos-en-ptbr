# Reproduzir o mod (contém detalhes técnicos e possíveis spoilers)

Fonte local: Clair Obscur Expedition 33 v1.5.2. O mod substitui somente `Sandfall/Content/Localization/Game/pt-BR/Game.locres`, no ponto de montagem `../../../`, por um pak V11 sem compressão. A interface deve estar em Português do Brasil. A seleção de áudio é independente deste pacote.

Resultado: 6.947 entradas recebem o inglês oficial, LF real, português oficial. 6.323 entradas portuguesas ficam intactas. As traduções são pareadas por namespace e chave e exigem o mesmo source hash. 155 chaves candidatas sem o par oficial são explicitamente omitidas no relatório. Nenhum recurso novo é traduzido ou inferido.

`ST_CS_`, `ST_IWD_`, `ST_BD_`, `ST_BK_` e `ST_BL_Entries` são as famílias de legendas. Em `ST_D_`/`ST_DS_`, somente chaves cuja constante é atribuída ao campo `FRichDialogueLine.LineText` em Blueprint que usa `StartRichDialogueLines` entram na lista permitida. Toda chave com qualquer outro uso de texto é bloqueada. O bloqueio também vale para as famílias de legendas. Os bytes dos campos, referências, caminhos e offsets usados na classificação estão em `classification_evidence.json`.

Uma escolha comprovada exige um array de constantes de texto passado imediatamente a `StartChoice`, referenciando o mesmo field path do array. As 345 chaves comprovadamente usadas em escolhas ficam intactas. Há 188 chaves com uso em fala e em outros contextos, das quais 61 também são escolhas comprovadas; todas permanecem portuguesas. O método é conservador e não garante duas línguas em todos os ramos possíveis. Nenhum Blueprint é alterado.

## Ferramentas portáteis oficiais

- Python 3.12, biblioteca padrão.
- repak v0.2.3: https://github.com/trumank/repak/releases/download/v0.2.3/repak_cli-x86_64-pc-windows-msvc.zip
- retoc v0.1.5: https://github.com/trumank/retoc/releases/download/v0.1.5/retoc_cli-x86_64-pc-windows-msvc.zip
- UnrealLocres, release 1.1.1 (o executável informa v1.1.0): https://github.com/akintos/UnrealLocres/releases/download/1.1.1/UnrealLocres.exe
- O formato binário locres segue https://github.com/akintos/UnrealLocres/blob/master/LocresLib/LocresFile.cs . O escritor preserva versão, prefixo de metadados, namespace/key hashes, source hashes, ordem e strings originais. Somente os índices selecionados e a tabela de strings são atualizados. O roundtrip sem modificações deve ser idêntico byte a byte.

UAssetGUI v1.1.0 foi usado apenas para conferência de NameMap e imports, não é necessário para reconstruir: https://github.com/atenfyr/UAssetGUI/releases/download/v1.1.0/UAssetGUI.exe . Os assets são unversioned; sem .usmap os exports ficam RawExport, por isso a classificação lê diretamente estruturas exatas do bytecode.

## Estrutura de trabalho e comandos

Os recursos originais e as ferramentas não são distribuídos neste pacote. Prepare uma pasta de trabalho com `tools/repak/repak.exe`, `tools/retoc/retoc.exe`, `tools/UnrealLocres.exe`. Os scripts podem permanecer na pasta `src`. Em PowerShell, ajuste estes três caminhos:

```powershell
$modBase = 'C:\caminho\trabalho'
$modScripts = 'C:\caminho\pacote\src'
$gamePaks = 'V:\caminho\game\Sandfall\Content\Paks'
& "$modBase\tools\repak\repak.exe" unpack "$gamePaks\pakchunk0-Windows.pak" -o "$modBase\extracted" -i 'Sandfall/Content/Localization/Game/'
& "$modBase\tools\retoc\retoc.exe" to-legacy $gamePaks "$modBase\dialogue_assets" -f 'Dialogue' --no-shaders
python "$modScripts\classify_dialogue.py" --base $modBase
python "$modScripts\build_mod.py" --base $modBase --extra-allowlist "$modBase\dialogue_allowlist.json" --blocklist "$modBase\dialogue_blocklist.json" --output "$modBase\candidate"
& "$modBase\tools\UnrealLocres.exe" export "$modBase\stage\Sandfall\Content\Localization\Game\pt-BR\Game.locres" -f csv -o "$modBase\independent_export.csv"
python "$modScripts\verify_mod.py" --base $modBase --report "$modBase\candidate\build_report.json" --independent-csv "$modBase\independent_export.csv"
```

O retoc pode precisar obter sua biblioteca de descompressão Oodle na primeira execução. Esses comandos apenas leem os paks do jogo e escrevem na pasta de trabalho. Não incluem instalação, alteração de configuração ou inicialização do jogo. O build só aceita locres versão 3 e aborta se houver duplicação de identidades ou divergência de source hashes. Os recursos de entrada devem coincidir com os SHA256 registrados em `build_report.json`; outra atualização do jogo exige nova revisão.

O `build_mod.py` verifica roundtrip, pareamento, igualdade exata dos dois idiomas, preservação das demais entradas e metadados, conteúdo único do pak e igualdade após extração. O `verify_mod.py` compara todas as 13.270 entradas com uma leitura independente por UnrealLocres e verifica que escolhas comprovadas e namespaces genéricos de interface ficam intactos. Nenhum desses testes confirma visualmente o ajuste das legendas na tela. Estatísticas de comprimento estão no relatório; o texto combinado pode alcançar 667 caracteres, exigindo quebra automática nativa.

`modified_pairs.json`, com o texto completo de todas as falas, permanece na pasta de trabalho do build para auditoria e não é necessário para instalar. Os relatórios de classificação podem revelar nomes internos e contexto de cenas.


Neste repositório, as listas desta versão estão em `data/` e os relatórios e evidências em `docs/tecnico/`. A classificação pode gerar novas listas diretamente na pasta de trabalho. Os arquivos originais extraídos do jogo e as ferramentas permanecem na pasta de trabalho local.
