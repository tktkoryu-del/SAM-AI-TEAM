import SwiftUI

// Native SwiftUI entry point; RTL is applied at the root view.

@main
struct SAMRecoveryApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView().environment(\.layoutDirection, .rightToLeft)
        }
    }
}