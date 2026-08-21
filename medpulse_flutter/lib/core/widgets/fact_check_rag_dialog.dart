import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';

/// Modal dialog displaying detailed RAG fact-checking results
class FactCheckRAGDialog extends StatelessWidget {
  final Map<String, dynamic> item;

  const FactCheckRAGDialog({super.key, required this.item});

  @override
  Widget build(BuildContext context) {
    final String verdict = (item['verdict'] ?? 'UNKNOWN').toString().toUpperCase();
    final bool isFalse = verdict == 'FALSE';
    final String claimText = (item['claim'] ?? '').toString().trim();
    final String explanationText = (item['explanation'] ?? item['summary'] ?? '').toString().trim();

    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(20.0),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header row: Status verdict badge and close button
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: isFalse ? Colors.red.shade100 : Colors.green.shade100,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      verdict,
                      style: TextStyle(
                        color: isFalse ? Colors.red.shade800 : Colors.green.shade800,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.of(context).pop(),
                  )
                ],
              ),
              const SizedBox(height: 12),
              
              // Verified claim title (Markdown formatted)
              MarkdownBody(
                data: claimText,
                selectable: true,
                styleSheet: MarkdownStyleSheet(
                  p: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: Colors.black87,
                    height: 1.35,
                  ),
                  strong: const TextStyle(
                    fontWeight: FontWeight.w900,
                    color: Colors.black,
                  ),
                ),
              ),
              const Divider(height: 24),

              // Evidentiary fact-check explanation header
              const Text(
                'AI Fact-Check Explanation:',
                style: TextStyle(
                  fontWeight: FontWeight.w600,
                  color: Colors.blueGrey,
                ),
              ),
              const SizedBox(height: 8),

              // Synthesized fact-check body (Markdown formatted)
              MarkdownBody(
                data: explanationText,
                selectable: true,
                styleSheet: MarkdownStyleSheet(
                  p: const TextStyle(
                    fontSize: 15,
                    height: 1.5,
                    color: Colors.black87,
                  ),
                  strong: const TextStyle(
                    fontWeight: FontWeight.bold,
                    color: Colors.black,
                  ),
                ),
              ),
              const SizedBox(height: 20),

              // Dismiss action button
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('Close'),
                ),
              )
            ],
          ),
        ),
      ),
    );
  }
}