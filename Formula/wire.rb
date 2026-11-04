# Homebrew formula for the Wire CLI (experimental, 5.0 alpha, wire#408).
#
# Lives in the public rittmananalytics/wire-plugin repository as Formula/wire.rb
# is the source of truth, published by the release step with the version and
# sha256 filled in. Install with:
#
#   brew tap rittmananalytics/wire https://github.com/rittmananalytics/wire-plugin
#   brew install wire
#
# The formula installs the packaged CLI and framework under libexec, a Python
# virtualenv with PyYAML (the resolver's one dependency), and the `wire`
# launcher. It does not install codex or claude; `wire doctor` says which are
# present.

class Wire < Formula
  include Language::Python::Virtualenv

  desc "Wire Framework CLI: the release loop for data platform engagements (experimental)"
  homepage "https://github.com/rittmananalytics/wire"
  url "https://github.com/rittmananalytics/wire-plugin/releases/download/v5.0.0-alpha.1/wire-cli-5.0.0-alpha.1.tar.gz"
  sha256 "311307e65f11bc868fea43847359200ed51fa06124c6bd27ccc1d7972c4212b0"
  license "FSL-1.1-ALv2"

  depends_on "python@3.12"

  resource "pyyaml" do
    url "https://files.pythonhosted.org/packages/source/P/PyYAML/pyyaml-6.0.2.tar.gz"
    sha256 "d584d9ec91ad65861cc08d42e834324ef890a082e591037abe114850ff7bbc3e"
  end

  def install
    venv = virtualenv_create(libexec/"venv", "python3.12")
    venv.pip_install resources
    (libexec/"wire").install Dir["*"]
    (bin/"wire").write <<~EOS
      #!/bin/sh
      exec "#{libexec}/venv/bin/python" "#{libexec}/wire/cli/wire.py" "$@"
    EOS
  end

  def caveats
    <<~EOS
      Wire runs its steps through an agent harness you install separately:
        codex   npm install -g @openai/codex
        claude  https://claude.com/claude-code
      Keys go in ~/.wire/secrets.env (see wire/cli/README.md). Run `wire doctor`.
    EOS
  end

  test do
    assert_match "wire 5.", shell_output("#{bin}/wire version")
  end
end
