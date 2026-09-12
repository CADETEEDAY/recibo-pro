import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:signature/signature.dart';
import 'pdf_generator.dart';

void main() => runApp(const ReciboApp());

class ReciboApp extends StatelessWidget {
  const ReciboApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Recibo Pro',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blueGrey),
        useMaterial3: true,
        inputDecorationTheme: const InputDecorationTheme(
          border: OutlineInputBorder(),
          filled: true,
          fillColor: Colors.white,
        ),
      ),
      home: const ReciboFormScreen(),
    );
  }
}

class ReciboFormScreen extends StatefulWidget {
  const ReciboFormScreen({super.key});

  @override
  State<ReciboFormScreen> createState() => _ReciboFormScreenState();
}

class _ReciboFormScreenState extends State<ReciboFormScreen> {
  final _formKey = GlobalKey<FormState>();

  final _emitenteController = TextEditingController();
  final _docEmitenteController = TextEditingController();
  final _pagadorController = TextEditingController();
  final _docPagadorController = TextEditingController();
  final _valorController = TextEditingController();
  final _referenteController = TextEditingController();

  late SignatureController _signatureController;
  String _dataAtual = '';
  String _numRecibo = '';

  @override
  void initState() {
    super.initState();
    _dataAtual = DateFormat('dd/MM/yyyy').format(DateTime.now());
    _numRecibo = DateTime.now().millisecondsSinceEpoch.toString().substring(7);
    _signatureController = SignatureController(
      penStrokeWidth: 3,
      penColor: Colors.black,
      exportBackgroundColor: Colors.transparent,
    );
  }

  @override
  void dispose() {
    _signatureController.dispose();
    super.dispose();
  }

  Future<void> _emitirRecibo() async {
    if (_formKey.currentState!.validate()) {
      Uint8List? signatureBytes;
      if (_signatureController.isNotEmpty) {
        signatureBytes = await _signatureController.toPngBytes();
      }
      if (!mounted) return;

      await PdfGenerator.gerarECompartilhar(
        context: context,
        numeroRecibo: _numRecibo,
        emitente: _emitenteController.text,
        documentoEmitente: _docEmitenteController.text,
        pagador: _pagadorController.text,
        documentoPagador: _docPagadorController.text,
        valor: _valorController.text,
        referente: _referenteController.text,
        data: _dataAtual,
        signatureBytes: signatureBytes,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey[100],
      appBar: AppBar(title: const Text('Novo Recibo Digital'), centerTitle: true),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Card(
                elevation: 0,
                shape: RoundedRectangleBorder(
                  side: BorderSide(color: Colors.grey.shade300),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Padding(
                  padding: const EdgeInsets.all(12.0),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text("Recibo Nº: $_numRecibo",
                          style: const TextStyle(fontWeight: FontWeight.bold)),
                      Text("Data: $_dataAtual"),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              const Text("Dados do Emitente",
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
              const SizedBox(height: 8),
              TextFormField(
                controller: _emitenteController,
                decoration: const InputDecoration(labelText: 'Seu Nome / Razão Social'),
                validator: (v) => v!.isEmpty ? 'Obrigatório' : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _docEmitenteController,
                decoration: const InputDecoration(labelText: 'Seu CPF / CNPJ'),
                keyboardType: TextInputType.number,
                validator: (v) => v!.isEmpty ? 'Obrigatório' : null,
              ),
              const SizedBox(height: 20),
              const Text("Dados do Pagador",
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
              const SizedBox(height: 8),
              TextFormField(
                controller: _pagadorController,
                decoration: const InputDecoration(labelText: 'Nome do Cliente'),
                validator: (v) => v!.isEmpty ? 'Obrigatório' : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _docPagadorController,
                decoration: const InputDecoration(labelText: 'CPF / CNPJ do Cliente'),
                keyboardType: TextInputType.number,
                validator: (v) => v!.isEmpty ? 'Obrigatório' : null,
              ),
              const SizedBox(height: 20),
              const Text("Detalhes do Pagamento",
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
              const SizedBox(height: 8),
              TextFormField(
                controller: _valorController,
                decoration: const InputDecoration(labelText: 'Valor (R\$)', prefixText: 'R\$ '),
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                validator: (v) => v!.isEmpty ? 'Obrigatório' : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _referenteController,
                maxLines: 3,
                decoration: const InputDecoration(labelText: 'Referente a...'),
                validator: (v) => v!.isEmpty ? 'Obrigatório' : null,
              ),
              const SizedBox(height: 20),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text("Assinatura na Tela",
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                  TextButton.icon(
                    onPressed: () => _signatureController.clear(),
                    icon: const Icon(Icons.clear, size: 18),
                    label: const Text('Limpar'),
                  ),
                ],
              ),
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: Container(
                  decoration: BoxDecoration(
                    color: Colors.white,
                    border: Border.all(color: Colors.grey.shade400),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Signature(
                    controller: _signatureController,
                    height: 140,
                    backgroundColor: Colors.white,
                  ),
                ),
              ),
              const SizedBox(height: 24),
              ElevatedButton.icon(
                onPressed: _emitirRecibo,
                icon: const Icon(Icons.picture_as_pdf),
                label: const Text('GERAR E COMPARTILHAR PDF',
                    style: TextStyle(fontWeight: FontWeight.bold)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.blueGrey[800],
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
