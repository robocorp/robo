package new

import (
	"fmt"
	"path"

	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/robocorp/robo/cli/config"
	"github.com/robocorp/robo/cli/environment"
	"github.com/robocorp/robo/cli/include"
	"github.com/robocorp/robo/cli/paths"
	"github.com/robocorp/robo/cli/rcc"
	"github.com/robocorp/robo/cli/ui"
	"github.com/robocorp/robo/cli/ui/choice"
	"github.com/robocorp/robo/cli/ui/progress"
)

type State int

const (
	StateTemplate State = iota
	StateName
	StateInstall
	StateDone
)

type model struct {
	currentState State

	root      string
	templates []include.Template
	template  *include.Template
	name      string
	dirName   string
	error     error

	templateInput   choice.Model
	nameInput       textinput.Model
	installProgress progress.Model
}

func NewProgram(dir string) *tea.Program {
	m := initialModel(dir)
	return tea.NewProgram(m)
}

func initialModel(dir string) model {
	templates := include.Templates()
	items := make([]choice.Option, len(templates))
	for i, t := range templates {
		items[i] = choice.Option{
			Title:       t.Name,
			Description: t.Description,
		}
	}

	templateInput := choice.New("Select template", items)
	nameInput := textinput.New()
	installProgress := progress.New()

	m := model{
		root:            dir,
		templates:       templates,
		templateInput:   templateInput,
		nameInput:       nameInput,
		installProgress: installProgress,
	}

	return m
}

func (m model) Init() tea.Cmd {
	return m.installProgress.PollEvents()
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		var cmd1, cmd2, cmd3 tea.Cmd
		m.templateInput, cmd1 = m.templateInput.Update(msg)
		m.nameInput, cmd2 = m.nameInput.Update(msg)
		m.installProgress, cmd3 = m.installProgress.Update(msg)
		return m, tea.Batch(cmd1, cmd2, cmd3)
	case tea.KeyMsg:
		if msg.Type == tea.KeyCtrlC {
			return m, tea.Quit
		}
	case ui.ErrorMsg:
		m.error = msg
		return m, tea.Quit
	}

	switch m.currentState {
	case StateTemplate:
		return m.updateStateTemplate(msg)
	case StateName:
		return m.updateStateName(msg)
	case StateInstall:
		return m.updateStateInstall(msg)
	case StateDone:
		return m, tea.Quit
	}

	return m, nil
}

func (m model) View() string {
	sections := make([]string, 0)

	switch m.currentState {
	case StateTemplate:
		sections = append(
			sections,
			m.templateInput.View(),
		)
	case StateName:
		dirName := paths.Sanitize(m.nameInput.Value())
		sections = append(
			sections,
			section("Selected template:", m.template.Name),
			"Project name:",
			m.nameInput.View(),
			faintText("Directory name:", dirName),
			faintText("\nPress ctrl-c to abort"),
		)
	case StateInstall:
		sections = append(
			sections,
			section("Selected template:", m.template.Name),
			section("Project name:", m.name),
			section("Directory name:", m.dirName),
			m.installProgress.View(),
			faintText("\nPress ctrl-c to abort"),
		)
	case StateDone:
		guide := ("Created project ✨\n" +
			faintText("To run the project ") +
			"cd " + m.dirName +
			faintText(" and then ") +
			"robo run")
		sections = append(
			sections,
			section("Selected template:", m.template.Name),
			section("Project name:", m.name),
			section("Directory name:", m.dirName),
			m.installProgress.ViewAs(1.0),
			"",
			guide,
			"",
		)
	}

	if m.error != nil {
		sections = append(sections, errorTitle("Error"), m.error.Error())
	}

	return margin.Render(
		lipgloss.JoinVertical(lipgloss.Left, sections...),
	)
}

func (m model) updateStateTemplate(msg tea.Msg) (tea.Model, tea.Cmd) {
	var cmd tea.Cmd
	m.templateInput, cmd = m.templateInput.Update(msg)

	if o := m.templateInput.SelectedOption(); o != nil {
		m.template = m.findTemplateByName(o.Title)
		m.currentState = StateName
		return m, tea.Batch(
			cmd,
			m.nameInput.Focus(),
			textinput.Blink,
		)
	}

	return m, cmd
}

func (m model) updateStateName(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		if msg.Type == tea.KeyEnter {
			value := m.nameInput.Value()
			if dirName := paths.Sanitize(value); len(dirName) > 0 {
				m.name = value
				m.dirName = dirName
				m.currentState = StateInstall
				return m, m.installProject()
			}
		}
	}

	var cmd tea.Cmd
	m.nameInput, cmd = m.nameInput.Update(msg)
	return m, cmd
}

func (m model) updateStateInstall(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg.(type) {
	case progress.ProgressDone:
		m.currentState = StateDone
		return m, tea.Quit
	}

	var cmd tea.Cmd
	m.installProgress, cmd = m.installProgress.Update(msg)
	return m, cmd
}

func (m model) installProject() tea.Cmd {
	ch := m.installProgress.EventChannel()
	onProgress := func(p *rcc.Progress) {
		ch <- progress.ProgressEvent{
			Current: p.Current,
			Total:   p.Total,
			Message: p.Message,
		}
	}

	return func() (msg tea.Msg) {
		defer func() {
			if r := recover(); r != nil {
				msg = ui.ErrorMsg(fmt.Errorf("%v", r))
			}
		}()

		dir := path.Join(m.root, m.dirName)
		if err := m.template.Copy(dir); err != nil {
			return ui.ErrorMsg(err)
		}
		cfg, err := config.FromPath(dir)
		if err != nil {
			return ui.ErrorMsg(err)
		}
		if _, ok := environment.TryCache(cfg); ok {
			ch <- progress.ProgressEvent{
				Current: 1,
				Total:   1,
				Message: "Found cached environment",
			}
			return nil
		}
		if _, err := environment.Create(cfg, onProgress); err != nil {
			return ui.ErrorMsg(err)
		}
		return nil
	}
}

func (m model) findTemplateByName(name string) *include.Template {
	for _, t := range m.templates {
		if t.Name == name {
			return &t
		}
	}
	return nil
}
