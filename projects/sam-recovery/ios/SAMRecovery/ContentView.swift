import SwiftUI
import Photos

struct MediaRow: Identifiable {
    let id: String
    let type: String
    let date: Date?
}

@MainActor
final class MediaLibraryModel: ObservableObject {
    @Published var rows: [MediaRow] = []
    @Published var message = "امنح الإذن لعرض الوسائط المتاحة."
    @Published var isLoading = false

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
                    VStack(alignment: .trailing, spacing: 5) {
                        Text(row.type).font(.headline)
                        if let date = row.date { Text(date.formatted(date: .abbreviated, time: .shortened)).font(.caption).foregroundStyle(.secondary) }
                    }
                }.listStyle(.plain)
            }.padding().toolbar(.hidden, for: .navigationBar)
        }
    }
}