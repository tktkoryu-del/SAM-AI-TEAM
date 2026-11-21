import SwiftUI
import Photos
import UIKit

struct MediaRow: Identifiable {
    let id: String
    let type: String
    let date: Date?
}

struct ShareItem: Identifiable {
    let id = UUID()
    let url: URL
}

@MainActor
final class MediaLibraryModel: ObservableObject {
    @Published var rows: [MediaRow] = []
    @Published var message = "امنح الإذن لعرض الوسائط المتاحة."
    @Published var isLoading = false
    @Published var shareItem: ShareItem?

    func scan() {
        let current = PHPhotoLibrary.authorizationStatus(for: .readWrite)
        if current == .notDetermined {
            PHPhotoLibrary.requestAuthorization(for: .readWrite) { [weak self] newStatus in
                Task { @MainActor in self?.load(status: newStatus) }
            }
        } else {
            load(status: current)
        }
    }

    private func load(status: PHAuthorizationStatus) {
        guard status == .authorized || status == .limited else {
            message = status == .denied ? "الإذن مرفوض. يمكنك تغييره من إعدادات iPhone." : "الوصول إلى مكتبة الصور غير متاح."
            rows = []
            return
        }
        isLoading = true
        let options = PHFetchOptions()
        options.sortDescriptors = [NSSortDescriptor(key: "creationDate", ascending: false)]
        let assets = PHAsset.fetchAssets(with: options)
        var found: [MediaRow] = []
        assets.enumerateObjects { asset, _, _ in
            guard asset.mediaType == .image || asset.mediaType == .video else { return }
            found.append(MediaRow(id: asset.localIdentifier, type: asset.mediaType == .video ? "فيديو" : "صورة", date: asset.creationDate))
        }
        rows = found
        isLoading = false
        message = "عُثر على \(found.count) عنصر متاح. لا يمكن للتطبيق الوصول مباشرة إلى ألبوم المحذوفة مؤخراً."
    }

    func prepareExport(for row: MediaRow) {
        guard let asset = PHAsset.fetchAssets(withLocalIdentifiers: [row.id], options: nil).firstObject,
              let resource = PHAssetResource.assetResources(for: asset).first else {
            message = "تعذر الوصول إلى الملف. تحقق من صلاحية مكتبة الصور."
            return
        }
        let safeName = URL(fileURLWithPath: resource.originalFilename).lastPathComponent
        let destination = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString + "-" + safeName)
        let options = PHAssetResourceRequestOptions()
        options.isNetworkAccessAllowed = true
        message = "جارٍ تجهيز نسخة للمشاركة أو الحفظ…"
        PHAssetResourceManager.default().writeData(for: resource, toFile: destination, options: options) { [weak self] error in
            Task { @MainActor in
                guard let self else { return }
                if let error {
                    self.message = "تعذر تجهيز الملف: \(error.localizedDescription)"
                } else {
                    self.shareItem = ShareItem(url: destination)
                    self.message = "اختر الحفظ في الملفات أو المشاركة من القائمة."
                }
            }
        }
    }
}

struct ShareSheet: UIViewControllerRepresentable {
    let activityItems: [Any]
    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: activityItems, applicationActivities: nil)
    }
    func updateUIViewController(_ controller: UIActivityViewController, context: Context) {}
}

struct ContentView: View {
    @StateObject private var model = MediaLibraryModel()

    var body: some View {
        NavigationStack {
            VStack(spacing: 16) {
                Text("SAM Recovery").font(.largeTitle.bold()).frame(maxWidth: .infinity, alignment: .trailing)
                Text("العثور على الصور والفيديوهات المتاحة").font(.headline).frame(maxWidth: .infinity, alignment: .trailing)
                Text("تنبيه: لا يمكن ضمان استعادة الملفات المحذوفة نهائياً. يفحص هذا الإصدار مكتبة الصور التي يسمح iOS بالوصول إليها فقط، ولا يرفع ملفاتك إلى الإنترنت.")
                    .font(.callout).padding().frame(maxWidth: .infinity, alignment: .trailing)
                    .background(Color.orange.opacity(0.14)).clipShape(RoundedRectangle(cornerRadius: 14))
                Button("ابدأ الفحص المحلي") { model.scan() }
                    .buttonStyle(.borderedProminent).frame(maxWidth: .infinity, alignment: .trailing)
                Text(model.message).font(.footnote).foregroundStyle(.secondary).frame(maxWidth: .infinity, alignment: .trailing)
                if model.isLoading { ProgressView() }
                List(model.rows) { row in
                    HStack {
                        VStack(alignment: .trailing, spacing: 5) {
                            Text(row.type).font(.headline)
                            if let date = row.date {
                                Text(date.formatted(date: .abbreviated, time: .shortened))
                                    .font(.caption).foregroundStyle(.secondary)
                            }
                        }
                        Spacer()
                        Button("تصدير") { model.prepareExport(for: row) }
                            .buttonStyle(.bordered)
                    }
                }.listStyle(.plain)
            }.padding()
                .toolbar(.hidden, for: .navigationBar)
                .sheet(item: $model.shareItem) { item in
                    ShareSheet(activityItems: [item.url])
                }
        }
    }
}
