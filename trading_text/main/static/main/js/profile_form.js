const facultySelect = document.querySelector("[name='faculty_group']");
const departmentSelect = document.querySelector("[name='department']");
const departmentData = document.getElementById("faculty-departments");

if (facultySelect && departmentSelect && departmentData) {
  const departmentsByFaculty = JSON.parse(departmentData.textContent);
  const initialDepartment = departmentSelect.value;

  const updateDepartments = (selectedDepartment = "") => {
    const departments = departmentsByFaculty[facultySelect.value] || [];
    departmentSelect.replaceChildren(new Option("学科を選択してください", ""));
    departments.forEach((department) => {
      departmentSelect.add(new Option(department, department, false, department === selectedDepartment));
    });
    departmentSelect.disabled = departments.length === 0;
  };

  updateDepartments(initialDepartment);
  facultySelect.addEventListener("change", () => updateDepartments());
}
