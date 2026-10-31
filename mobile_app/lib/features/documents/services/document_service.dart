import 'dart:convert';
import 'dart:typed_data';
import 'package:http/http.dart' as http;
import '../../../core/network/api_endpoints.dart';
import '../../../core/services/secure_storage_service.dart';
import '../models/document_models.dart';

class DocumentService {
  static final DocumentService _instance = DocumentService._internal();
  factory DocumentService() => _instance;
  DocumentService._internal();

  final SecureStorageService _storage = SecureStorageService();

  Future<Map<String, String>> _buildHeaders({bool isJson = true}) async {
    final token = await _storage.getAccessToken();
    final headers = <String, String>{
      'Accept': 'application/json',
    };
    if (isJson) {
      headers['Content-Type'] = 'application/json';
    }
    if (token != null) {
      headers['Authorization'] = 'Bearer $token';
    }
    return headers;
  }

  /// Upload a document file to the vault with OCR processing
  Future<DocumentMetadataModel> uploadDocument({
    required Uint8List fileBytes,
    required String filename,
    required String documentType,
  }) async {
    final uri = Uri.parse('${ApiEndpoints.baseUrl}${ApiEndpoints.documentUpload}');
    final request = http.MultipartRequest('POST', uri);

    final token = await _storage.getAccessToken();
    if (token != null) {
      request.headers['Authorization'] = 'Bearer $token';
    }
    request.headers['Accept'] = 'application/json';

    request.fields['document_type'] = documentType;

    final multipartFile = http.MultipartFile.fromBytes(
      'file',
      fileBytes,
      filename: filename,
    );
    request.files.add(multipartFile);

    try {
      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);
      final body = jsonDecode(response.body);

      if (response.statusCode == 201) {
        final docJson = body['document'] as Map<String, dynamic>;
        return DocumentMetadataModel.fromJson(docJson);
      } else {
        final errorMsg = body['detail'] ?? 'Failed to upload document.';
        throw Exception(errorMsg);
      }
    } catch (e) {
      if (e is Exception) rethrow;
      throw Exception('Network or upload error: $e');
    }
  }

  /// List citizen's uploaded documents with optional filters
  Future<List<DocumentMetadataModel>> getDocuments({
    String? documentType,
    String? ocrStatus,
  }) async {
    final queryParams = <String, String>{};
    if (documentType != null && documentType.isNotEmpty && documentType != 'all') {
      queryParams['document_type'] = documentType;
    }
    if (ocrStatus != null && ocrStatus.isNotEmpty && ocrStatus != 'ALL') {
      queryParams['ocr_status'] = ocrStatus;
    }

    final uri = Uri.parse('${ApiEndpoints.baseUrl}${ApiEndpoints.documents}')
        .replace(queryParameters: queryParams.isNotEmpty ? queryParams : null);

    try {
      final headers = await _buildHeaders();
      final response = await http.get(uri, headers: headers);
      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        final list = (data['documents'] as List<dynamic>? ?? [])
            .map((item) => DocumentMetadataModel.fromJson(item as Map<String, dynamic>))
            .toList();
        return list;
      } else {
        final message = data['detail'] ?? 'Failed to load documents.';
        throw Exception(message);
      }
    } catch (e) {
      if (e is Exception) rethrow;
      throw Exception('Network error while retrieving documents: $e');
    }
  }

  /// Get specific document details and OCR text
  Future<DocumentMetadataModel> getDocumentDetail(String documentId) async {
    final uri = Uri.parse('${ApiEndpoints.baseUrl}${ApiEndpoints.documentDetail(documentId)}');
    try {
      final headers = await _buildHeaders();
      final response = await http.get(uri, headers: headers);
      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return DocumentMetadataModel.fromJson(data as Map<String, dynamic>);
      } else {
        final message = data['detail'] ?? 'Document not found.';
        throw Exception(message);
      }
    } catch (e) {
      if (e is Exception) rethrow;
      throw Exception('Error loading document: $e');
    }
  }

  /// Delete document from vault
  Future<void> deleteDocument(String documentId) async {
    final uri = Uri.parse('${ApiEndpoints.baseUrl}${ApiEndpoints.documentDetail(documentId)}');
    try {
      final headers = await _buildHeaders();
      final response = await http.delete(uri, headers: headers);
      if (response.statusCode != 200) {
        final data = jsonDecode(response.body);
        final message = data['detail'] ?? 'Failed to delete document.';
        throw Exception(message);
      }
    } catch (e) {
      if (e is Exception) rethrow;
      throw Exception('Error deleting document: $e');
    }
  }

  /// Retry OCR extraction on existing document
  Future<DocumentMetadataModel> retryOcr(String documentId) async {
    final uri = Uri.parse('${ApiEndpoints.baseUrl}${ApiEndpoints.documentRetryOcr(documentId)}');
    try {
      final headers = await _buildHeaders();
      final response = await http.post(uri, headers: headers);
      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return DocumentMetadataModel.fromJson(data as Map<String, dynamic>);
      } else {
        final message = data['detail'] ?? 'Failed to re-process OCR.';
        throw Exception(message);
      }
    } catch (e) {
      if (e is Exception) rethrow;
      throw Exception('Error re-running OCR: $e');
    }
  }

  /// Check scheme document requirements against user's vault
  Future<SchemeDocumentChecklistModel> getSchemeDocumentChecklist(String schemeId) async {
    final uri = Uri.parse('${ApiEndpoints.baseUrl}${ApiEndpoints.schemeDocumentChecklist(schemeId)}');
    try {
      final headers = await _buildHeaders();
      final response = await http.get(uri, headers: headers);
      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return SchemeDocumentChecklistModel.fromJson(data as Map<String, dynamic>);
      } else {
        final message = data['detail'] ?? 'Failed to load document checklist.';
        throw Exception(message);
      }
    } catch (e) {
      if (e is Exception) rethrow;
      throw Exception('Error retrieving checklist: $e');
    }
  }
}

