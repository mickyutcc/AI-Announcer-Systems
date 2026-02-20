/* eslint-disable @next/next/no-img-element */
export default function HeroSection(){ 
   return ( 
     <div className="page-container"> 
       <div className="hero"> 
         <img src="/logo.svg" alt="MuseGenx1000" className="logo" /> 
         <h1>MuseGenx1000</h1> 
         <p className="lead">AI Music Studio • Professional Grade</p> 
       </div> 
 
       <div className="card"> 
         <h3>เข้าสู่ระบบ</h3> 
         <input className="input" placeholder="ชื่อผู้ใช้" /> 
         <input className="input" placeholder="รหัสผ่าน" type="password" /> 
         <div style={{display:'flex', gap:12}}> 
           <button className="btn">เข้าสู่ระบบ</button> 
           <button className="btn secondary">สมัครสมาชิก</button> 
         </div> 
       </div> 
     </div> 
   ) 
 }
