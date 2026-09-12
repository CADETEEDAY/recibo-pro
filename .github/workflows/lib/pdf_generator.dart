import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;
import 'package:printing/printing.dart';

class PdfGenerator {
  static Future<void> gerarECompartilhar({
    required BuildContext context,
    required String numeroRecibo,
    required String emitente,
    required String documentoEmitente,
    required String pagador,
    required String documentoPagador,
    required String valor,
    required String referente,
    required String data,
    Uint8List? signatureBytes,
  }) async {
    final pdf = pw.Document();

    pdf.addPage(
      pw.Page(
        pageFormat: PdfPageFormat.a4,
        build: (pw.Context context) {
          return pw.Container(
            padding: const pw.EdgeInsets.all(24),
            decoration: pw.BoxDecoration(
              border: pw.Border.all(color: PdfColors.blueGrey800, width: 2),
              borderRadius: const pw.BorderRadius.all(pw.Radius.circular(8)),
            ),
            child: pw.Column(
              cross: pw.CrossAxisAlignment.start,
              children: [
                // Cabecalho
                pw.Row(
                  mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
                  children: [
                    pw.Column(
                      cross: pw.CrossAxisAlignment.start,
                      children: [
                        pw.Text(
                          "RECIBO DE PAGAMENTO",
                          style: pw.TextStyle(
                            fontSize: 22,
                            fontWeight: pw.FontWeight.bold,
                            color: PdfColors.blueGrey900,
                          ),
                        ),
                        pw.Text("Nº: $numeroRecibo",
                            style: const pw.TextStyle(fontSize: 12)),
                      ],
                    ),
                    pw.Container(
                      padding: const pw.EdgeInsets.symmetric(
                          horizontal: 16, vertical: 8),
                      decoration: const pw.BoxDecoration(
                        color: PdfColors.grey200,
                        borderRadius:
                            pw.BorderRadius.all(pw.Radius.circular(4)),
                      ),
                      child: pw.Text(
                        "VALOR: R\$ $valor",
                        style: pw.TextStyle(
                          fontSize: 18,
                          fontWeight: pw.FontWeight.bold,
                          color: PdfColors.black,
                        ),
                      ),
                    ),
                  ],
                ),
                pw.Divider(thickness: 1, height: 32),

                // Corpo
                pw.Paragraph(
                  text:
                      "Recebi(emos) de $pagador, inscrito(a) no CPF/CNPJ sob o nº $documentoPagador, a importância de R\$ $valor.",
                  style: const pw.TextStyle(fontSize: 14, lineSpacing: 1.5),
                ),
                pw.SizedBox(height: 12),
                pw.Paragraph(
                  text: "Referente a: $referente.",
                  style: const pw.TextStyle(fontSize: 14, lineSpacing: 1.5),
                ),
                pw.SizedBox(height: 12),
                pw.Paragraph(
                  text:
                      "Para clareza e firmeza do que foi acordado, firmo(amos) o presente recibo dando plena e geral quitação.",
                  style: const pw.TextStyle(fontSize: 12, lineSpacing: 1.4),
                ),

                pw.Spacer(),

                // Linha de Data e Assinatura
                pw.Row(
                  mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
                  crossAxisAlignment: pw.CrossAxisAlignment.end,
                  children: [
                    pw.Column(
                      cross: pw.CrossAxisAlignment.start,
                      children: [
                        pw.Text("Data: $data",
                            style: const pw.TextStyle(fontSize: 12)),
                      ],
                    ),
                    pw.Column(
                      children: [
                        if (signatureBytes != null)
                          pw.Container(
                            height: 60,
                            width: 180,
                            child: pw.Image(
                              pw.MemoryImage(signatureBytes),
                              fit: pw.BoxFit.contain,
                            ),
                          )
                        else
                          pw.SizedBox(height: 60),

                        pw.Container(
                          width: 220,
                          decoration: const pw.BoxDecoration(
                            border: pw.Border(
                              bottom: pw.BorderSide(
                                  color: PdfColors.black, width: 1),
                            ),
                          ),
                        ),
                        pw.SizedBox(height: 6),
                        pw.Text(emitente,
                            style: pw.TextStyle(
                                fontSize: 12,
                                fontWeight: pw.FontWeight.bold)),
                        pw.Text("Doc: $documentoEmitente",
                            style: const pw.TextStyle(fontSize: 10)),
                      ],
                    ),
                  ],
                ),
              ],
            ),
          );
        },
      ),
    );

    await Printing.sharePdf(
      bytes: await pdf.save(),
      filename: 'recibo_$numeroRecibo.pdf',
    );
  }
}
